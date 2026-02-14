# Phase 2: Data Ingestion — Verification Checklist

Run through this checklist yourself AFTER Cursor says Phase 2 is complete.  
Every item must pass before moving to Phase 3.

---

## Docker & Infrastructure

- [ ] `docker-compose up --build` starts all 5 services (db, redis, backend, frontend, worker) without errors
- [ ] Celery worker logs show "ready" and is connected to Redis
- [ ] All Phase 1 tests still pass (nothing broken)

---

## CSV Upload — Small File (Sync)

- [ ] Create a test CSV with 10 rows and columns like "feedback", "email", "company", "date"
- [ ] Upload it through the frontend
- [ ] Feedback items appear in the feedback list immediately (no waiting)
- [ ] Each item shows the correct content, source type "csv", and author info
- [ ] The column mapping was auto-detected correctly

---

## CSV Upload — Large File (Async)

- [ ] Create a test CSV with 600+ rows (duplicate rows are fine for testing)
- [ ] Upload it through the frontend
- [ ] You see a progress indicator (not a frozen screen)
- [ ] Progress updates over time (processed rows count goes up)
- [ ] When done, status shows "completed"
- [ ] All rows appear in the feedback list
- [ ] Upload the same file again — duplicates are NOT created

---

## CSV Upload — Error Handling

- [ ] Upload a .txt or .pdf file — get a clear error, not a crash
- [ ] Upload a CSV with no recognizable "content" column — get a clear error asking you to specify
- [ ] Upload a CSV where some rows have missing data — batch completes, failed_rows count is correct, other rows are fine

---

## Manual Input

- [ ] Open the manual feedback form
- [ ] Submit with only the feedback text (required field) — it works
- [ ] Submit with all fields filled (name, email, company, source) — all fields saved correctly
- [ ] Submit with empty feedback text — get a validation error
- [ ] The item appears in the feedback list with source type "manual"

---

## Slack Integration

- [ ] Settings page shows "Connect Slack" button when not connected
- [ ] Clicking it starts the OAuth flow (redirects to Slack)
- [ ] After approving in Slack, you're redirected back to settings
- [ ] Settings now shows workspace name and "Connected" status
- [ ] Channel list loads and you can select channels to monitor
- [ ] Send a message in a monitored Slack channel
- [ ] The message appears as a feedback item with source type "slack", correct author name and email
- [ ] Send the same message again (or edit it) — no duplicate created
- [ ] Bot messages in the channel are NOT ingested
- [ ] "Disconnect" button works and status returns to not connected

---

## Feedback List Page

- [ ] Shows all feedback items regardless of source
- [ ] Each item shows: content (truncated), source type badge, author name, timestamp
- [ ] Pagination works (if you have enough items, next/previous pages work)
- [ ] Filter by source type works (All / Slack / CSV / Manual)
- [ ] Clicking a feedback item shows its full details
- [ ] Only YOUR organization's feedback shows (not another org's)

---

## Batch Tracking

- [ ] GET /api/v1/batches returns list of your CSV uploads
- [ ] Each batch shows: filename, total rows, processed rows, successful rows, failed rows, status
- [ ] Batch from another org is NOT visible

---

## Navigation

- [ ] Left sidebar now has: Dashboard, Feedback, Settings
- [ ] All three links work and load the correct page
- [ ] "Add Feedback" option is available on the feedback page (upload CSV or add manually)

---

## Security

- [ ] Check the database directly: Slack access_token column is encrypted (not plain text)
- [ ] Try accessing another org's feedback via API with your token — returns 404 or empty, not their data
- [ ] Try accessing another org's batch — returns 404 or empty

---

## Quick API Spot Checks

Open http://localhost:8000/docs (Swagger) and test:

- [ ] GET /api/v1/feedback — returns paginated list
- [ ] GET /api/v1/feedback/{id} — returns single item
- [ ] POST /api/v1/feedback/manual — creates item
- [ ] GET /api/v1/batches — returns batch list
- [ ] GET /api/v1/batches/{id} — returns batch with progress
- [ ] GET /api/v1/slack/status — returns connection status
- [ ] All error responses follow the shape: `{ "error": { "code": "...", "message": "..." } }`

---

## Tests

- [ ] All Phase 2 backend tests pass
- [ ] All Phase 1 backend tests still pass
- [ ] Run: `docker compose exec backend pytest app/tests/ -v`

---

## If Something Fails

Tell Cursor: *"Phase 2 checklist item [X] failed. Here's what happened: [describe]. Fix it following the spec in docs/PHASE_2_SPEC.md."*

Once everything passes, move to Phase 3.
