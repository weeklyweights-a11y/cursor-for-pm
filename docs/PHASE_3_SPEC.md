# Phase 3: Signal Extraction

> **Goal:** Every feedback item that enters the system automatically gets structured signals extracted from it: pain point, topic, related feature, feature gap, urgency, sentiment, and a key quote. A PM sets up their product context once during onboarding, and the LLM uses that context to understand every piece of feedback.
>
> **Done means:** After a PM completes the onboarding form (product description, existing features, known limitations), every new feedback item — whether from CSV, manual input, or Slack — automatically gets extraction fields filled in within seconds. The PM can see extracted signals on each feedback item in the UI. Extraction works with Ollama locally and can be switched to Claude API via one environment variable.

---

## Context for the AI Agent

This is Phase 3 of 8. Phases 1 and 2 are complete — you have authentication, multi-tenant org model, feedback ingestion from CSV/manual/Slack, Celery workers, and batch processing.

In this phase you are adding the intelligence layer. Raw feedback text goes in, structured signals come out. This is the first time the system uses an LLM.

Read `.cursorrules` before starting. All rules apply.

**Project root:** `D:\LinkedIn\Week4`

---

## What You Are Building

Three things:

1. **Product context onboarding** — A form where the PM describes their product, lists existing features, and notes known limitations. Stored once, used in every extraction prompt.

2. **LLM service abstraction** — A single interface that all LLM calls go through. Swap between Ollama (local, free) and Claude API (cloud, paid) with one environment variable. No other code changes needed.

3. **Extraction pipeline** — A Celery task that runs automatically after feedback is ingested. Takes each feedback item, combines it with the PM's product context, sends it to the LLM, and saves the structured output back to the feedback_items table.

---

## New Dependencies to Add

| Package | Purpose |
|---------|---------|
| httpx (already installed) | HTTP client for calling Ollama REST API |
| anthropic | Official Anthropic Python SDK for Claude API calls (used in production) |

---

## Docker Compose Changes

Add one new service:

**`ollama` — Local LLM Server**
- Use the official Ollama Docker image.
- Expose port 11434.
- Mount a named volume for model storage (so models persist between restarts).
- No GPU required for Llama 3.2 3B (runs on CPU, but will be slow — expect 15-30 seconds per extraction. This is fine for development).
- After the container starts, the model needs to be pulled. Add an instruction in the README or a startup script that runs `ollama pull llama3.2:3b` on first setup.

**Why Llama 3.2 3B Instruct instead of NuExtract:**
NuExtract is a pure extraction model — it copies text from input into JSON fields. Your extraction task requires reasoning (inferring urgency from language, classifying sentiment, deciding if a feature is new or existing, synthesizing what's missing). Llama 3.2 3B handles classification and reasoning tasks well for its size. Production quality comes from Claude Haiku via API — the local model is for development and testing only.

**New environment variables:**

| Variable | Dev Value | Prod Value | Purpose |
|----------|-----------|------------|---------|
| LLM_PROVIDER | ollama | anthropic | Which LLM backend to use |
| OLLAMA_BASE_URL | http://ollama:11434 | (not used) | Ollama API endpoint |
| OLLAMA_MODEL | llama3.2:3b | (not used) | Which Ollama model to use |
| ANTHROPIC_API_KEY | (empty) | sk-ant-xxx | Claude API key (only needed in production) |
| ANTHROPIC_EXTRACTION_MODEL | claude-haiku-4-5-20251001 | claude-haiku-4-5-20251001 | Claude model for extraction (fast, cheap) |
| LLM_TIMEOUT_SECONDS | 30 | 30 | Timeout for LLM calls |
| LLM_MAX_RETRIES | 1 | 1 | Retries on LLM failure |

---

## Database Changes

### New Table: product_contexts

Stores the PM's product description used in extraction prompts. One per organization.

| Column | Type | Rules |
|--------|------|-------|
| id | UUID (PK) | Auto-generated |
| org_id | UUID (FK to organizations) | Required, unique (one context per org), indexed |
| product_name | string | Required. Name of the product. |
| product_description | text | Required. What the product does in 2-3 sentences. |
| existing_features | text[] | Required. List of features the product currently has. |
| target_users | string | Nullable. Who the product is for. |
| known_limitations | text[] | Nullable. Known issues or missing capabilities. |
| additional_context | text | Nullable. Any extra context the PM wants the LLM to know. |
| created_at | timestamptz | Auto-generated |
| updated_at | timestamptz | Auto-generated |

### Alter Table: feedback_items

Add new columns to the existing feedback_items table. Create a new Alembic migration for these columns. Do not recreate the table.

| Column | Type | Set By | Rules |
|--------|------|--------|-------|
| pain_point | text | Layer 2 | Nullable. What the customer is struggling with. |
| topic | string | Layer 2 | Nullable. Category (search, authentication, performance, etc.). |
| related_feature | string | Layer 2 | Nullable. Which feature this relates to. |
| is_existing_feature | boolean | Layer 2 | Nullable. True if about an existing feature, false if a new request. |
| feature_gap | text | Layer 2 | Nullable. What's missing. |
| urgency | string (enum: low, medium, high, critical) | Layer 2 | Nullable. |
| sentiment | string (enum: positive, neutral, negative) | Layer 2 | Nullable. |
| verbatim_quote | text | Layer 2 | Nullable. Key quote from the feedback. |
| extraction_confidence | float | Layer 2 | Nullable. 0.0 to 1.0. Model's confidence in the extraction. |
| extraction_status | string (enum: pending, completed, failed) | Layer 2 | Default "pending". |
| raw_llm_response | text | Layer 2 | Nullable. Full raw LLM output for debugging. |
| extracted_at | timestamptz | Layer 2 | Nullable. When extraction completed. |

**Index:** Add index on (org_id, extraction_status) for querying unextracted items.

---

## LLM Service Abstraction

This is the most important architectural piece in this phase. Every LLM call in the entire system (extraction, matching, naming, scoring, briefs, solutions, specs) will go through this interface. Build it right.

### Interface

Create `backend/app/services/llm_service.py`

This service must expose a single function:

`call_llm(prompt, system_prompt, expected_schema, temperature, max_tokens) -> dict`

What it does:
- Reads LLM_PROVIDER from config.
- If "ollama": calls the Ollama REST API at OLLAMA_BASE_URL with OLLAMA_MODEL.
- If "anthropic": calls the Anthropic Python SDK with the configured model and API key.
- Applies timeout from LLM_TIMEOUT_SECONDS.
- Parses the response as JSON.
- If JSON parsing fails (LLM returned markdown fences, or plain text, or truncated output):
  - Strip markdown code fences if present.
  - Try parsing again.
  - If still fails, retry once (up to LLM_MAX_RETRIES).
  - If retry also fails, raise an ExternalServiceError with the raw response logged.
- Always return a dict with the parsed JSON.
- Always log: provider, model, duration_ms, success/failure, prompt length (not the prompt content itself).

### What This Service Does NOT Do

- It does not know about feedback, themes, or any business domain. It just sends prompts and returns parsed JSON.
- It does not store anything in the database. The caller stores results.
- It does not decide which model to use for which task. The caller passes the config or the service reads from env vars.

### Provider-Specific Details

**Ollama:**
- Endpoint: POST {OLLAMA_BASE_URL}/api/chat (use the chat endpoint, not generate, since Llama 3.2 is an instruct/chat model).
- Send: model name, messages array (system message + user message), temperature (set to 0 for consistent extraction), format: "json".
- Ollama's chat endpoint supports a "format" parameter that tells it to return JSON.
- Parse the response body's "message.content" field.
- Important: Set temperature to 0. Extraction should be deterministic.

**Anthropic:**
- Use the anthropic Python SDK.
- Create a client with the ANTHROPIC_API_KEY.
- Call client.messages.create with model, system prompt, user message (the prompt), max_tokens, temperature.
- Extract the text content from the response.
- Parse as JSON.

### How to Test Locally Without Ollama Running

For tests, create a mock LLM service that returns predefined JSON responses. The test suite should never make actual LLM calls. Use dependency injection or a mock flag in config.

---

## Product Context Onboarding

### When It Happens

The PM fills this out the first time they use the product, right after signup. It is also accessible from the Settings page to update later.

### Onboarding Flow

1. After first login, if no product_context exists for the org, redirect to an onboarding page.
2. PM fills in: product name, product description, existing features (as a comma-separated list or tag input), target users, known limitations (as a list), any additional context.
3. On submit, store in product_contexts table.
4. Redirect to the dashboard.
5. PM can update this anytime from Settings.

### API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/v1/product-context | Yes | Get the current org's product context. Returns 404 if not set up yet. |
| POST | /api/v1/product-context | Yes | Create product context (first time). Returns 400 if already exists. |
| PATCH | /api/v1/product-context | Yes | Update product context. |

---

## Extraction Pipeline

### How It's Triggered

Extraction runs automatically after a feedback item is ingested. The trigger is:

- **Manual input:** After the feedback item is created in the API route, queue an extraction Celery task for that item.
- **CSV upload (sync):** After all rows are created, queue extraction tasks for all items in the batch.
- **CSV upload (async):** After each chunk is processed by the CSV Celery task, queue extraction tasks for the items in that chunk.
- **Slack message:** After the Slack Celery task creates the feedback item, queue an extraction task for it.

Extraction tasks should be queued individually per feedback item (not one task for the entire batch). This way, if one item fails, others still process.

### What If Product Context Doesn't Exist?

If the PM hasn't completed onboarding (no product_context for this org), extraction still runs but without product context. The LLM prompt will say "No product context provided" and extraction quality will be lower. The system should not block ingestion because onboarding isn't done.

### Extraction Flow (Per Feedback Item)

1. Load the feedback item from the database.
2. Check extraction_status. If already "completed", skip (idempotency).
3. Load the product context for this org (if it exists).
4. Build the extraction prompt (see below).
5. Call the LLM service.
6. Validate the response against the expected schema.
7. If valid: update the feedback item with all extracted fields, set extraction_status to "completed", set extracted_at to now, store raw_llm_response.
8. If invalid (schema mismatch, missing required fields): set extraction_status to "failed", store raw_llm_response, log the error.
9. Log: feedback_id, org_id, extraction_status, confidence, duration_ms.

### Extraction Prompt

The prompt sent to the LLM must include:

**System prompt:** You are an expert product analyst. You extract structured signals from customer feedback. You always respond in valid JSON matching the exact schema provided. Never include any text outside the JSON object.

**User prompt contents:**
- The product context (name, description, existing features, known limitations) — if available.
- The feedback text.
- The expected output schema with field descriptions:
  - pain_point: What the customer is struggling with. One sentence.
  - topic: Category of the feedback. One or two words. Examples: search, authentication, performance, onboarding, pricing, mobile, integrations.
  - related_feature: Which existing or requested feature this relates to. Use feature names from the product context if possible.
  - is_existing_feature: true if the feedback is about a feature that already exists, false if it's a request for something new.
  - feature_gap: What's missing or broken. One sentence. Null if no clear gap.
  - urgency: low, medium, high, or critical. Based on language intensity, words like "blocking", "deadline", "immediately", "critical".
  - sentiment: positive, neutral, or negative.
  - verbatim_quote: The most important sentence or phrase from the feedback. Copy it exactly.
  - confidence: Your confidence in this extraction, 0.0 to 1.0.

**Important prompt rules:**
- The prompt must NOT include other customer feedback (only the single item being extracted).
- The prompt must NOT include any PII from other customers.
- The prompt must tell the LLM to respond with JSON only — no markdown fences, no explanation text.

### Prompt Template

Store the extraction prompt as a template file at `backend/app/prompts/extraction.py` (or `.txt`). Use `{variable}` placeholders that get filled at runtime. Do not construct the prompt with string concatenation inside the service function. The prompt will be iterated on frequently, so it must be easy to find and edit.

### Validation of LLM Output

After parsing the JSON response, validate:
- `pain_point` is a non-empty string.
- `topic` is a non-empty string.
- `urgency` is one of: low, medium, high, critical.
- `sentiment` is one of: positive, neutral, negative.
- `is_existing_feature` is a boolean.
- `confidence` is a number between 0.0 and 1.0.

If any required field is missing or invalid, treat the extraction as failed. Store the raw response for debugging.

---

## Services

### extraction_service.py

Functions:
- `extract_signals(db, feedback_item_id, org_id)` — Load item, load product context, build prompt, call LLM, validate response, save results. Returns the updated feedback item.
- `build_extraction_prompt(feedback_content, product_context)` — Load the prompt template, fill in variables, return the complete prompt.
- `validate_extraction_result(result)` — Check that LLM output matches expected schema. Return (is_valid, errors).
- `get_extraction_stats(db, org_id)` — Return counts: total items, pending, completed, failed. Used for dashboard.

### product_context_service.py

Functions:
- `create_product_context(db, org_id, data)` — Create new context. Raise AlreadyExistsError if one exists.
- `get_product_context(db, org_id)` — Get context for org. Raise NotFoundError if not set.
- `update_product_context(db, org_id, data)` — Update existing context.
- `has_product_context(db, org_id)` — Return boolean. Used to check if onboarding is needed.

---

## Tasks (Celery)

### tasks/extraction_tasks.py

One task:
- `extract_feedback_signals(feedback_item_id, org_id)` — Call extraction_service.extract_signals. Handle errors gracefully (log, set status to failed, do not crash). This task is queued by ingestion routes and tasks after creating feedback items.

### Modify Existing Tasks

**tasks/csv_tasks.py** — After each chunk of CSV rows is created, queue extract_feedback_signals for each new feedback item.

**tasks/slack_tasks.py** — After creating the feedback item from a Slack message, queue extract_feedback_signals for it.

### Modify Existing Routes

**routes/feedback.py (manual input)** — After creating the feedback item, queue extract_feedback_signals for it.

---

## Schemas (Pydantic)

### schemas/product_context.py

- `ProductContextCreateRequest` — product_name (required), product_description (required), existing_features (required, list of strings), target_users (optional), known_limitations (optional, list of strings), additional_context (optional).
- `ProductContextResponse` — All fields from the table.
- `ProductContextUpdateRequest` — All fields optional (partial update).

### schemas/feedback.py (update existing)

- Update `FeedbackItemResponse` to include all new extraction fields (pain_point, topic, urgency, sentiment, etc.).
- Add `ExtractionStatsResponse` — total, pending, completed, failed counts.

---

## Models

### New Model

- `backend/app/models/product_context.py` — ProductContext model matching the table above.

### Updated Model

- `backend/app/models/feedback_item.py` — Add all new extraction columns to the existing model.

---

## Alembic Migrations

Two migrations:

**`003_create_product_contexts`** — Create the product_contexts table.

**`004_add_extraction_fields_to_feedback_items`** — Add all extraction columns to the existing feedback_items table. All new columns must be nullable (existing rows won't have extraction data yet).

---

## Frontend Changes

### Onboarding Page (`frontend/src/pages/OnboardingPage.tsx`)

- Shows after first login if product context doesn't exist.
- Form fields: Product name, Product description (textarea), Existing features (tag-style input where PM types a feature and presses enter to add it to a list), Target users, Known limitations (same tag-style input), Additional context (textarea).
- All required fields clearly marked.
- Submit button creates the product context and redirects to dashboard.
- Clean, welcoming design. This is the PM's first real interaction with the product after signup.

### Settings Page (update existing)

- Add a "Product Context" section above or below the Slack section.
- Shows current product context in a readable format.
- "Edit" button opens an inline edit form or modal.
- PM can update any field and save.

### Feedback List (update existing)

- Each feedback item in the list now shows extraction badges:
  - Topic badge (e.g., "search", "authentication")
  - Urgency badge with color (critical=red, high=orange, medium=yellow, low=gray)
  - Sentiment indicator (negative=red dot, neutral=gray dot, positive=green dot)
- Items with extraction_status "pending" show a small spinner or "Processing..." label.
- Items with extraction_status "failed" show a warning icon.

### Feedback Detail View (update existing or new component)

- When PM clicks on a feedback item, show full details including:
  - Original feedback text (full content)
  - Pain point
  - Topic
  - Related feature
  - Is existing feature (yes/no badge)
  - Feature gap
  - Urgency (with color)
  - Sentiment (with color)
  - Verbatim quote (highlighted or in a callout box)
  - Extraction confidence (as percentage)
  - Source info (type, author, timestamp)

### Router Updates

- Add `/onboarding` route → OnboardingPage (protected, but redirects to dashboard if product context already exists).
- Update the app to check for product context on login. If missing, redirect to onboarding before dashboard.

### Dashboard Update

- Add an extraction stats card to the dashboard: "Extraction: X completed, Y pending, Z failed out of N total."
- This gives the PM a quick view of processing status.

---

## Testing

### test_llm_service.py
1. Call with Ollama provider and valid prompt returns parsed JSON (mock the HTTP call).
2. Call with Anthropic provider and valid prompt returns parsed JSON (mock the SDK call).
3. LLM returns markdown-fenced JSON — service strips fences and parses successfully.
4. LLM returns invalid JSON — service retries once.
5. LLM returns invalid JSON on retry — service raises ExternalServiceError.
6. LLM call exceeds timeout — service raises ExternalServiceError.
7. Parsed JSON missing required field — validation catches it.

### test_extraction_service.py
1. Extract signals for a feedback item with product context — all fields populated correctly.
2. Extract signals for a feedback item without product context — still works, lower confidence acceptable.
3. Extract signals for an item already completed — skips (idempotency).
4. LLM returns invalid urgency value — extraction marked as failed.
5. LLM returns valid response — extraction_status set to completed, extracted_at set, raw_llm_response stored.
6. Build extraction prompt includes product context when available.
7. Build extraction prompt handles missing product context gracefully.
8. Get extraction stats returns correct counts.

### test_product_context_service.py
1. Create product context for an org — stored correctly.
2. Create product context when one already exists — returns error.
3. Get product context — returns correct data.
4. Update product context — fields updated.
5. Has product context returns true when exists, false when not.
6. Product context filtered by org_id (multi-tenant isolation).

### test_extraction_routes.py
1. POST /feedback/manual now triggers extraction (verify extraction task is queued — mock Celery).
2. GET /feedback/{id} returns extraction fields when completed.
3. GET /feedback/{id} returns extraction_status "pending" for unextracted items.

### test_product_context_routes.py
1. POST /product-context creates context.
2. POST /product-context when already exists returns 400.
3. GET /product-context returns context for authenticated user's org.
4. GET /product-context when not set returns 404.
5. PATCH /product-context updates fields.
6. Product context from another org is not accessible.

---

## Non-Negotiable Rules for This Phase

Everything from Phases 1 and 2 still applies, plus:

1. **LLM service is provider-agnostic.** No Ollama-specific or Anthropic-specific code outside of llm_service.py. Every other service calls `call_llm()` and doesn't know or care which provider is behind it.
2. **Prompt templates live in their own files.** Not constructed inline in service functions. Easy to find, easy to edit.
3. **Raw LLM responses are always stored.** Every extraction saves raw_llm_response, even on success. This is critical for debugging extraction quality.
4. **LLM output is always validated.** Never trust the LLM to return the right shape. Parse, validate, handle failures.
5. **Extraction is idempotent.** Running extraction twice on the same item produces the same result (skips if already completed).
6. **Extraction never blocks ingestion.** If the LLM is slow or down, feedback still gets ingested. Extraction runs asynchronously and catches up.
7. **No customer PII in logs.** Log feedback_item_id and org_id, not the feedback content or customer names.
8. **LLM calls have timeouts.** 30 seconds default. One retry on failure. Then mark as failed and move on.

---

## What NOT to Build

- Customer matching or enrichment (Phase 4)
- Embeddings or vector storage (Phase 5)
- Clustering or theme creation (Phase 5)
- Scoring or prioritization (Phase 5)
- Chat functionality (Phase 6)
- Brief generation (Phase 7)
- Solution design (Phase 7)
- Spec generation (Phase 8)

---

## Acceptance Criteria

Phase 3 is complete when ALL of these are true:

- [ ] Ollama container starts and the Llama 3.2 3B model is available (`ollama pull llama3.2:3b`)
- [ ] LLM_PROVIDER=ollama makes LLM calls go to Ollama
- [ ] LLM_PROVIDER=anthropic makes LLM calls go to Claude API (test with mock or real key)
- [ ] Switching providers requires only changing the env var — no code changes
- [ ] PM can complete the onboarding form and product context is stored
- [ ] First login redirects to onboarding if no product context exists
- [ ] PM can update product context from Settings page
- [ ] New manual feedback item triggers extraction automatically
- [ ] New CSV upload triggers extraction for all ingested items
- [ ] New Slack message triggers extraction after ingestion
- [ ] Extracted feedback items show pain_point, topic, urgency, sentiment, and other fields
- [ ] Extraction failures are marked as "failed" with raw_llm_response stored
- [ ] Items that already have extraction completed are not re-extracted (idempotency)
- [ ] Feedback list shows topic badges, urgency colors, and sentiment indicators
- [ ] Feedback detail view shows all extraction fields
- [ ] Dashboard shows extraction stats (completed, pending, failed)
- [ ] Pending items show a processing indicator in the UI
- [ ] LLM timeout is enforced (30 seconds)
- [ ] LLM retries once on failure, then marks as failed
- [ ] Prompt template is in its own file, not inline in code
- [ ] All Phase 3 tests pass
- [ ] All Phase 1 and Phase 2 tests still pass

---

## How to Give This to Cursor

1. Save this file as `D:\LinkedIn\Week4\docs\PHASE_3_SPEC.md`
2. Open Cursor's chat and type:

> Read `docs/PHASE_3_SPEC.md`. This is the spec for Phase 3. The `.cursorrules` file still applies. Do NOT start building yet. Create a detailed implementation plan first: list every file you will create or modify, what each contains, the order of work, and dependencies. Present the full plan and wait for my approval.

3. Review the plan. Approve or push back.
4. Let Cursor build.
5. Run through acceptance criteria.

---

## After Phase 3

Once all acceptance criteria pass, come back for Phase 4: Enrichment. That phase will add:
- Customer CSV upload and customers table
- Smart matching (exact domain, saved mappings, LLM fuzzy match, PM review queue)
- Domain mappings table
- Enrichment fields on feedback_items (customer_id, segment, match_status, etc.)
- Enrichment runs after extraction completes
