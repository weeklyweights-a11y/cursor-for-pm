# Phase 2: Data Ingestion

> **Goal:** PMs can get feedback into the system from three sources: CSV upload, manual text input, and Slack. Large CSVs process asynchronously with progress tracking. Every feedback item lands in the same unified table regardless of source.
>
> **Done means:** A PM can upload a small CSV and see feedback items appear instantly. A PM can upload a large CSV (1000+ rows) and see a progress bar while it processes in the background. A PM can paste feedback manually through a form. A PM can connect their Slack workspace and feedback from selected channels flows in automatically. All feedback lands in the `feedback_items` table with the same shape.

---

## Context for the AI Agent

This is Phase 2 of 8. Phase 1 is complete — you have a working FastAPI backend, React frontend, Postgres, Redis, JWT auth, and multi-tenant org model.

In this phase you are building the data ingestion layer. This is where all customer feedback enters the system. Every future layer (extraction, enrichment, clustering, prioritization) depends on this layer producing clean, consistent data.

Read `.cursorrules` before starting. All naming, file size, error handling, logging, and testing rules apply.

**Project root:** `D:\LinkedIn\Week4`

---

## What You Are Building

Three ingestion paths that all produce the same output:

| Source | User Experience | Processing Mode |
|--------|----------------|-----------------|
| CSV upload (under 500 rows) | PM uploads file, sees feedback appear within seconds | Synchronous |
| CSV upload (500+ rows) | PM uploads file, sees a progress bar, can navigate away and come back | Asynchronous (Celery background job) |
| Manual input | PM fills a form, clicks submit, feedback appears instantly | Synchronous |
| Slack | PM connects workspace via OAuth, selects channels, feedback flows in automatically | Asynchronous (webhook events) |

---

## New Dependencies to Add

Add these to the backend requirements file. Do not remove existing dependencies.

| Package | Purpose |
|---------|---------|
| celery | Background job processing for async CSV and Slack events |
| pandas | CSV parsing — handles edge cases, encoding issues, large files |
| slack-bolt | Official Slack SDK for OAuth and Events API |
| slack-sdk | Low-level Slack API client (used by slack-bolt) |
| python-multipart | File upload handling in FastAPI (may already be installed from Phase 1) |

---

## Docker Compose Changes

Add one new service to docker-compose.yml:

**`worker` — Celery Worker**
- Build from the same backend Dockerfile (same codebase).
- Depends on `db` and `redis`.
- Runs Celery worker process (not uvicorn).
- Mount the same backend source code volume for hot-reload during development.
- Load the same .env file.
- This service processes background jobs: large CSV parsing, Slack event handling.

Do not modify the existing 4 services (db, redis, backend, frontend) except to add any new environment variables.

**New environment variables to add to .env:**

| Variable | Value | Purpose |
|----------|-------|---------|
| CELERY_BROKER_URL | redis://redis:6379/0 | Celery uses Redis as message broker |
| CELERY_RESULT_BACKEND | redis://redis:6379/1 | Celery stores job results in Redis |
| SLACK_CLIENT_ID | (empty for now) | Slack app OAuth client ID |
| SLACK_CLIENT_SECRET | (empty for now) | Slack app OAuth secret |
| SLACK_SIGNING_SECRET | (empty for now) | Slack request verification |
| MAX_SYNC_CSV_ROWS | 500 | Threshold: below this = sync, above = async |
| MAX_CSV_FILE_SIZE_MB | 50 | Maximum CSV upload size |

---

## Database Changes

Create new Alembic migrations for these tables. Do not modify the existing organizations and users tables.

### feedback_items Table

This is the core table of the entire system. Every layer reads from and writes to it. Design it carefully.

| Column | Type | Set By | Rules |
|--------|------|--------|-------|
| id | UUID (PK) | System | Auto-generated |
| org_id | UUID (FK to organizations) | System | Required, indexed. Multi-tenant isolation. |
| content | text | Layer 1 | Required. The raw feedback text. |
| source_type | string (enum: slack, csv, manual) | Layer 1 | Required, indexed |
| source_id | string | Layer 1 | Nullable. Original ID from source system (Slack message ts, CSV row number). Used for deduplication. |
| timestamp | timestamptz | Layer 1 | Required. When the feedback was originally created (not when we ingested it). |
| author_email | string | Layer 1 | Nullable. Email of the person who gave feedback. |
| author_name | string | Layer 1 | Nullable. Name of the person. |
| organization_name | string | Layer 1 | Nullable. Company name if available from source. |
| metadata | JSONB | Layer 1 | Nullable. Source-specific data (channel name, thread_id, CSV filename, row number, etc.) |
| batch_id | UUID (FK to batches) | Layer 1 | Nullable. Null for non-CSV sources. Links to the batch this item came from. |
| created_at | timestamptz | System | Auto-generated |
| updated_at | timestamptz | System | Auto-generated |

**Indexes:** org_id, source_type, batch_id, (org_id + source_type) composite, (org_id + source_id) unique composite for deduplication.

**Important:** This table will gain many more columns in later phases (Layers 2-4 will add extraction fields, enrichment fields, embedding vectors, and theme assignments). Do not add those columns now. They come in later migrations.

### batches Table

Tracks CSV upload jobs — status, progress, errors.

| Column | Type | Rules |
|--------|------|-------|
| id | UUID (PK) | Auto-generated |
| org_id | UUID (FK to organizations) | Required, indexed |
| filename | string | Required. Original filename the PM uploaded. |
| total_rows | integer | Required. Total rows detected in CSV. |
| processed_rows | integer | Default 0. Updated as chunks complete. |
| successful_rows | integer | Default 0. Rows that were parsed and stored successfully. |
| failed_rows | integer | Default 0. Rows that failed to parse. |
| status | string (enum: pending, processing, completed, failed) | Default "pending". |
| error_message | text | Nullable. Error description if status is "failed". |
| column_mapping | JSONB | Nullable. Stores the detected or confirmed column-to-field mapping. |
| created_at | timestamptz | Auto-generated |
| updated_at | timestamptz | Auto-generated |

### slack_connections Table

Stores Slack workspace OAuth tokens and channel configurations per organization.

| Column | Type | Rules |
|--------|------|-------|
| id | UUID (PK) | Auto-generated |
| org_id | UUID (FK to organizations) | Required, unique (one Slack workspace per org), indexed |
| team_id | string | Required. Slack workspace ID. |
| team_name | string | Required. Slack workspace name. |
| access_token | string | Required. Encrypted. Bot OAuth token. |
| bot_user_id | string | Required. Bot user ID in the workspace. |
| incoming_channels | JSONB | Default empty array. List of channel IDs the PM selected to monitor. |
| is_active | boolean | Default true. |
| created_at | timestamptz | Auto-generated |
| updated_at | timestamptz | Auto-generated |

**Security:** The access_token must be encrypted at rest. Use Fernet symmetric encryption with a key from environment variables. Add an `ENCRYPTION_KEY` env var.

---

## Celery Setup

### Celery App Configuration

Create a Celery app instance in the backend. It should:
- Use Redis as the broker (from CELERY_BROKER_URL env var).
- Use Redis as the result backend (from CELERY_RESULT_BACKEND env var).
- Auto-discover tasks from the `backend/app/tasks/` directory.
- Be importable from `backend/app/celery_app.py` or similar.

### Task Files

Create a tasks directory: `backend/app/tasks/`

Each task file contains Celery task functions. The tasks call service functions for the actual logic — tasks are thin wrappers, just like routes.

---

## CSV Upload Flow

### Step 1: PM Uploads a CSV

**Endpoint: `POST /api/v1/feedback/upload-csv`**
- Requires authentication.
- Accepts a file upload (multipart form data).
- Validate: file must be .csv extension, file size must be under MAX_CSV_FILE_SIZE_MB.
- Read the file and detect the total number of rows.

### Step 2: Detect Columns

Before processing rows, the system must figure out which CSV column maps to which feedback field. Use keyword matching on the column headers:

| Feedback Field | Column Names to Match (case-insensitive) |
|---------------|------------------------------------------|
| content (the feedback text) | feedback, message, text, description, content, body, comment, note, request |
| author_email | email, customer_email, user_email, requester_email, contact_email |
| author_name | name, customer_name, user_name, requester_name, contact_name, author |
| organization_name | company, customer, organization, org, account, company_name, org_name |
| timestamp | date, created, created_at, timestamp, time, submitted, submitted_at |

**If the "content" column cannot be detected** (no header matches), return an error asking the PM to specify which column contains the feedback text. This is the only required field.

**If other columns cannot be detected**, that's fine — those fields will be null for those rows.

Store the detected column mapping in the batch record's `column_mapping` field.

### Step 3: Process Based on Size

**If total rows <= MAX_SYNC_CSV_ROWS (default 500):**
- Process synchronously in the same request.
- Parse each row using the column mapping.
- Create feedback_items records.
- Return the completed batch with item count.

**If total rows > MAX_SYNC_CSV_ROWS:**
- Create a batch record with status "pending".
- Save the uploaded CSV file temporarily (to a temp directory or store contents in Redis).
- Queue a Celery task to process the CSV.
- Return the batch_id immediately so the frontend can poll for progress.

### Step 4: Async Processing (Celery Task)

The Celery task for large CSV processing must:
- Read the CSV in chunks (500 rows per chunk).
- For each chunk: parse rows, create feedback_items records, update batch.processed_rows.
- If a row fails to parse, increment batch.failed_rows and continue (do not stop the whole batch).
- When all chunks are done, update batch.status to "completed".
- If a fatal error occurs (file corrupt, database down), update batch.status to "failed" with error_message.
- Log: batch_id, chunk number, rows processed, duration_ms.

### Step 5: Deduplication

Before inserting a feedback item from CSV, check if a record with the same (org_id, source_id) already exists. The source_id for CSV items is `{batch_id}:{row_number}`. If it exists, skip it. This prevents duplicates if a batch is retried.

---

## Manual Input Flow

**Endpoint: `POST /api/v1/feedback/manual`**
- Requires authentication.
- Accepts JSON body with:
  - `content` (required): The feedback text.
  - `author_name` (optional): Who gave this feedback.
  - `author_email` (optional): Their email.
  - `organization_name` (optional): Their company.
  - `source_description` (optional): Where this came from (e.g., "Sales call with BigCorp").
- Creates a single feedback_item with source_type="manual".
- Returns the created feedback item.
- No deduplication needed (PM intentionally submits each time).

---

## Slack Integration Flow

### Step 1: OAuth Connection

**Endpoint: `GET /api/v1/slack/install`**
- Requires authentication.
- Redirects the PM to Slack's OAuth authorization page.
- Slack asks the PM to select a workspace and approve permissions.
- Scopes needed: `channels:history`, `channels:read`, `users:read`, `users:read.email`.

**Endpoint: `GET /api/v1/slack/oauth/callback`**
- Slack redirects here after PM approves.
- Exchange the temporary code for a bot access token.
- Store the token (encrypted) in slack_connections table.
- Redirect PM back to the frontend settings page.

### Step 2: Channel Selection

**Endpoint: `GET /api/v1/slack/channels`**
- Requires authentication.
- Uses the stored bot token to call Slack API and list all public channels in the workspace.
- Returns the list so the PM can select which channels to monitor.

**Endpoint: `POST /api/v1/slack/channels`**
- Requires authentication.
- Accepts a list of channel IDs.
- Updates the slack_connection's incoming_channels field.
- The bot joins those channels (via Slack API).

### Step 3: Receiving Messages

**Endpoint: `POST /api/v1/slack/events`**
- This is the Slack Events API webhook endpoint.
- No JWT auth (Slack sends these directly). Instead, verify using Slack signing secret.
- Handle Slack's URL verification challenge (Slack sends a challenge on first setup; respond with the challenge value).
- For `message` events in monitored channels:
  - Ignore bot messages (check for bot_id in the event).
  - Ignore message edits and deletes (only process new messages).
  - Extract: message text, user ID, channel ID, timestamp.
  - Queue a Celery task to process the message (do not process synchronously — Slack requires a quick 200 response).

### Step 4: Processing a Slack Message (Celery Task)

The Celery task must:
- Fetch the user's profile from Slack API (using bot token) to get their email and real name.
- Check for deduplication: does a feedback_item with source_id = `{channel_id}:{message_ts}` already exist for this org? If yes, skip.
- Create a feedback_item with:
  - content = message text
  - source_type = "slack"
  - source_id = `{channel_id}:{message_ts}`
  - author_email = from Slack user profile
  - author_name = from Slack user profile
  - timestamp = message timestamp converted to datetime
  - metadata = { channel_id, channel_name, thread_ts (if threaded), team_id }
- Log: source_type, channel_name, user (masked email), success/failure.

---

## API Endpoints Summary

All endpoints prefixed with `/api/v1/`.

### Feedback

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /feedback/upload-csv | Yes | Upload a CSV file. Returns batch with items (sync) or batch_id (async). |
| POST | /feedback/manual | Yes | Submit a single feedback item manually. |
| GET | /feedback | Yes | List feedback items for the current org. Paginated. Filterable by source_type. |
| GET | /feedback/{id} | Yes | Get a single feedback item. |

### Batches

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /batches | Yes | List all CSV upload batches for the current org. Paginated. |
| GET | /batches/{id} | Yes | Get batch status (pending/processing/completed/failed), progress (processed_rows/total_rows), and error if any. |

### Slack

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /slack/install | Yes | Start Slack OAuth flow (redirect to Slack). |
| GET | /slack/oauth/callback | No (Slack redirect) | Handle OAuth callback, store token, redirect to frontend. |
| GET | /slack/channels | Yes | List available Slack channels. |
| POST | /slack/channels | Yes | Select channels to monitor. |
| POST | /slack/events | No (Slack webhook) | Receive Slack events. Verified by signing secret. |
| GET | /slack/status | Yes | Check if Slack is connected for this org. Returns connection status and monitored channels. |
| DELETE | /slack/disconnect | Yes | Disconnect Slack (deactivate connection, clear token). |

### Response Shapes

Follow the response shapes from `.cursorrules`:

**List endpoints** return paginated results with `data` array and `pagination` object.

**Single item endpoints** return `{ "data": { ... } }`.

**Batch status** returns `{ "data": { "id": "...", "status": "processing", "total_rows": 10000, "processed_rows": 4500, "successful_rows": 4480, "failed_rows": 20, "filename": "feedback.csv" } }`.

---

## Frontend Changes

### New Pages

**Feedback Page (`frontend/src/pages/FeedbackPage.tsx`)**

The main page PMs see after ingesting data. Shows:
- A table/list of all feedback items for their org.
- Each row shows: content (truncated to ~100 chars), source type (with icon or badge: Slack/CSV/Manual), author name, timestamp.
- Pagination controls.
- Filter by source type (All, Slack, CSV, Manual).
- Click a row to see the full feedback item details.

**Upload Page or Modal (`frontend/src/pages/UploadPage.tsx` or component)**

- Drag-and-drop zone for CSV files (or click to select file).
- After file is selected, show file name and size.
- Upload button.
- If sync (small file): show a loading spinner, then redirect to feedback list when done.
- If async (large file): show a progress bar that polls `GET /batches/{id}` every 2 seconds. Show: "Processing 4,500 of 10,000 items..." When done, show success message and link to feedback list.
- If error: show the error message from the batch.

**Manual Input Form (component or page)**

- Simple form: feedback text (required, textarea), author name, author email, organization name, source description (all optional).
- Submit button.
- On success: show confirmation and clear form. Optionally show the created item.

**Settings Page (`frontend/src/pages/SettingsPage.tsx`)**

- Slack connection section:
  - If not connected: "Connect Slack" button that triggers the OAuth flow.
  - If connected: show workspace name, list of monitored channels, button to change channels, "Disconnect" button.
- This page will grow in later phases (product context, customer upload, scoring weights).

### Layout Updates

- Add navigation links in the left sidebar: "Dashboard", "Feedback", "Settings".
- "Feedback" links to the feedback page.
- "Settings" links to the settings page.
- Add an "Add Feedback" button or dropdown in the top area of the feedback page with options: "Upload CSV" and "Add Manually".

### Router Updates

Add new routes:
- `/feedback` → FeedbackPage (protected)
- `/settings` → SettingsPage (protected)

---

## Services (Backend)

### feedback_service.py

Functions:
- `create_feedback_item(db, org_id, data)` — Creates a single feedback item. Used by manual input and Slack processing.
- `create_feedback_items_batch(db, org_id, items)` — Creates multiple feedback items in one transaction. Used by CSV processing.
- `get_feedback_items(db, org_id, page, page_size, source_type_filter)` — List with pagination and optional filtering.
- `get_feedback_item(db, org_id, item_id)` — Get single item. Must filter by org_id.
- `check_duplicate(db, org_id, source_id)` — Check if source_id already exists for this org.

### batch_service.py

Functions:
- `create_batch(db, org_id, filename, total_rows, column_mapping)` — Create a new batch record.
- `update_batch_progress(db, batch_id, processed_rows, successful_rows, failed_rows)` — Update progress.
- `complete_batch(db, batch_id)` — Set status to completed.
- `fail_batch(db, batch_id, error_message)` — Set status to failed with error.
- `get_batch(db, org_id, batch_id)` — Get batch. Must filter by org_id.
- `get_batches(db, org_id, page, page_size)` — List batches for org.

### csv_service.py

Functions:
- `detect_columns(headers)` — Match CSV headers to feedback fields using keyword matching. Return a mapping dict.
- `parse_csv_row(row, column_mapping)` — Convert a CSV row to a feedback item dict using the mapping.
- `parse_csv_file(file_content, column_mapping, chunk_size)` — Generator that yields chunks of parsed rows.

### slack_service.py

Functions:
- `start_oauth(org_id)` — Generate the Slack OAuth URL with correct scopes and state.
- `handle_oauth_callback(db, org_id, code)` — Exchange code for token, store encrypted connection.
- `get_channels(db, org_id)` — Use stored token to list workspace channels.
- `set_monitored_channels(db, org_id, channel_ids)` — Update incoming_channels and join channels.
- `process_slack_message(db, org_id, event)` — Fetch user profile, create feedback item, deduplicate.
- `get_connection_status(db, org_id)` — Return connection status and channel list.
- `disconnect(db, org_id)` — Deactivate connection, clear token.

### encryption_service.py

Functions:
- `encrypt(plain_text)` — Encrypt using Fernet with ENCRYPTION_KEY from env.
- `decrypt(encrypted_text)` — Decrypt using Fernet.
- Used for Slack access tokens.

---

## Tasks (Celery)

### tasks/csv_tasks.py

One task:
- `process_csv_batch(batch_id, org_id, file_path_or_content, column_mapping)` — Read CSV in chunks, parse rows, create feedback items, update batch progress. Handle errors per-row (skip bad rows, continue). Update batch status on completion or failure. Log progress.

### tasks/slack_tasks.py

One task:
- `process_slack_event(org_id, event_data)` — Fetch user profile, check for duplicates, create feedback item. Log result.

---

## Schemas (Pydantic)

### schemas/feedback.py

- `ManualFeedbackRequest` — content (required), author_name, author_email, organization_name, source_description (all optional).
- `FeedbackItemResponse` — All fields from feedback_items table.
- `FeedbackListResponse` — List of FeedbackItemResponse with pagination.

### schemas/batch.py

- `BatchResponse` — All fields from batches table.
- `BatchListResponse` — List of BatchResponse with pagination.
- `CSVUploadResponse` — Either the completed batch (sync) or batch_id with status "pending" (async).

### schemas/slack.py

- `SlackChannelResponse` — channel_id, channel_name, is_monitored.
- `SlackChannelListResponse` — List of channels.
- `SlackChannelSelectRequest` — List of channel_ids to monitor.
- `SlackConnectionStatusResponse` — is_connected, team_name, monitored_channels, connected_at.

---

## Models (SQLAlchemy)

Create new model files:

- `backend/app/models/feedback_item.py` — FeedbackItem model matching the table above.
- `backend/app/models/batch.py` — Batch model matching the table above.
- `backend/app/models/slack_connection.py` — SlackConnection model matching the table above.

Update the models `__init__.py` to export the new models.

---

## Alembic Migration

Create a new migration: `002_create_feedback_items_batches_slack_connections`

This migration creates:
- feedback_items table with all columns and indexes.
- batches table with all columns and indexes.
- slack_connections table with all columns and indexes.
- Foreign keys: feedback_items.org_id → organizations.id, feedback_items.batch_id → batches.id, batches.org_id → organizations.id, slack_connections.org_id → organizations.id.

---

## Testing

### test_feedback_service.py
1. Create a manual feedback item — verify it's stored with correct fields.
2. Create multiple feedback items in batch — verify all stored.
3. List feedback items filters by org_id (multi-tenant isolation).
4. List feedback items filters by source_type.
5. Pagination works correctly.
6. Duplicate source_id is detected.

### test_csv_service.py
1. Column detection correctly maps known header names.
2. Column detection handles case-insensitive matching.
3. Column detection handles unknown headers (returns partial mapping with content required).
4. Parse CSV row converts row to feedback item dict correctly.
5. Parse CSV row handles missing optional fields gracefully.

### test_batch_service.py
1. Create batch sets status to pending.
2. Update progress increments processed_rows.
3. Complete batch sets status to completed.
4. Fail batch sets status to failed with error message.
5. Get batch filters by org_id (multi-tenant isolation).

### test_feedback_routes.py
1. POST /feedback/manual with valid data creates item and returns 200.
2. POST /feedback/manual without content returns 422.
3. POST /feedback/upload-csv with small CSV returns completed batch with items.
4. POST /feedback/upload-csv with large CSV returns batch_id with pending status.
5. POST /feedback/upload-csv with non-CSV file returns 400.
6. POST /feedback/upload-csv with oversized file returns 400.
7. GET /feedback returns paginated list filtered by org_id.
8. GET /feedback with source_type filter works.
9. GET /feedback/{id} returns the item if it belongs to current org.
10. GET /feedback/{id} for another org's item returns 404.
11. GET /batches returns batches for current org.
12. GET /batches/{id} returns batch with progress.

### test_slack_routes.py
1. GET /slack/status when not connected returns is_connected: false.
2. GET /slack/channels when not connected returns error.
3. POST /slack/events with valid signing secret is accepted.
4. POST /slack/events with invalid signing secret is rejected.
5. Slack message creates feedback item with correct fields (mock Slack API calls).
6. Duplicate Slack message is not ingested twice.

### test_encryption_service.py
1. Encrypt and decrypt returns original value.
2. Decrypt with wrong key fails.

---

## Non-Negotiable Rules for This Phase

Everything from Phase 1 still applies, plus:

1. **Every feedback query filters by org_id.** A PM must never see feedback from another organization.
2. **CSV processing must not block the API.** Large files go through Celery. The API returns immediately.
3. **Failed rows do not kill the batch.** If row 5000 has bad data, skip it, increment failed_rows, continue with row 5001.
4. **Slack tokens are encrypted at rest.** Never store plain text OAuth tokens in the database.
5. **Slack events endpoint verifies the signing secret.** Never trust unverified Slack webhooks.
6. **Deduplication by source_id.** Same Slack message or same CSV row in the same batch is never ingested twice.
7. **All Celery tasks are idempotent.** If a task runs twice for the same input, the result is the same (no duplicate records).
8. **Log every ingestion.** Source type, item count, org_id, duration_ms, success/failure.

---

## What NOT to Build

- Signal extraction / LLM calls on feedback (Phase 3)
- Customer matching or enrichment (Phase 4)
- Embeddings or clustering (Phase 5)
- Any scoring or prioritization (Phase 5)
- Chat functionality (Phase 6)
- Brief generation (Phase 7)
- Spec generation (Phase 8)
- Product context / onboarding form (Phase 3)

The feedback_items table will gain more columns in later phases. Do not add them now.

---

## Acceptance Criteria

Phase 2 is complete when ALL of these are true:

- [ ] Celery worker starts successfully alongside the other Docker services
- [ ] PM can upload a small CSV (under 500 rows) and see feedback items appear in the feedback list
- [ ] PM can upload a large CSV (500+ rows) and see a batch with status progressing from pending → processing → completed
- [ ] CSV column auto-detection correctly maps common header names to feedback fields
- [ ] PM can submit manual feedback through the form and see it in the feedback list
- [ ] Feedback list shows all items with source type badges, pagination, and source type filtering
- [ ] PM can start Slack OAuth flow and connect their workspace
- [ ] PM can select which Slack channels to monitor
- [ ] Slack messages in monitored channels create feedback items automatically
- [ ] Duplicate Slack messages and CSV rows are not ingested twice
- [ ] Batch progress tracking works (processed_rows updates as chunks complete)
- [ ] Failed CSV rows are skipped without killing the batch
- [ ] Slack tokens are encrypted in the database
- [ ] Slack events endpoint rejects requests with invalid signing secret
- [ ] GET /feedback filters by org_id (multi-tenant isolation verified by test)
- [ ] GET /batches filters by org_id (multi-tenant isolation verified by test)
- [ ] Settings page shows Slack connection status and channel management
- [ ] Left sidebar navigation includes Feedback and Settings links
- [ ] All backend tests pass
- [ ] All existing Phase 1 tests still pass (nothing broken)

---

## How to Give This to Cursor

1. Save this file as `D:\LinkedIn\Week4\docs\PHASE_2_SPEC.md`
2. Open Cursor's chat and type:

> Read `docs/PHASE_2_SPEC.md`. This is the spec for Phase 2. The `.cursorrules` file still applies. Do NOT start building yet. First, create a detailed implementation plan: list every file you will create or modify, what each contains, the order you will work in, and dependencies between files. Present the full plan and wait for my approval before writing any code.

3. Review the plan. Push back on anything that deviates from this spec.
4. Once approved, tell Cursor to start building.
5. After completion, run through the acceptance criteria.

---

## After Phase 2

Once all acceptance criteria pass, come back for Phase 3: Signal Extraction. That phase will add:
- Ollama container to Docker Compose
- LLM service abstraction (Ollama locally, Claude API in production)
- Product context setup (onboarding form)
- Automatic extraction of pain points, topics, urgency, sentiment from every feedback item
- New columns on feedback_items table for extracted fields
- Extraction runs as Celery task triggered after ingestion
