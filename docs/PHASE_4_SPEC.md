# Phase 4: Customer Enrichment

> **Goal:** Feedback gets linked to real customer profiles. PMs upload their customer list, and the system automatically matches feedback to customers using a 5-step smart matching flow. The system learns from every match so it gets faster and more accurate over time.
>
> **Done means:** A PM uploads a CSV of their customers (domain, company name, segment). New and existing feedback items get automatically matched to customer profiles. Exact domain matches happen instantly. Fuzzy matches use the LLM. Uncertain matches go to a PM review queue. Every confirmed match is saved so the same pair is never asked about again. The PM can see which customers are requesting what, filtered by segment.

---

## Context for the AI Agent

This is Phase 4 of 8. Phases 1-3 are complete — you have authentication, multi-tenant orgs, feedback ingestion from CSV/manual/Slack, Celery background jobs, LLM service abstraction (Ollama locally, Claude API in production), product context onboarding, and automatic signal extraction.

In this phase you are adding customer identity to feedback. Until now, feedback items have author_email and organization_name from the source, but no link to actual customer records. This phase creates that link.

Read `.cursorrules` before starting. All rules apply.

**Project root:** `D:\LinkedIn\Week4`

---

## What You Are Building

Three things:

1. **Customer data management** — PM uploads a CSV of their customers. Each customer has a domain, company name, and segment (SMB, mid-market, enterprise). This is the source of truth for who the PM's customers are.

2. **Smart matching pipeline** — A 5-step flow that matches each feedback item to a customer record. Runs automatically after extraction completes. Gets smarter over time by saving learned mappings.

3. **PM review queue** — When the system isn't confident enough to auto-match, it queues the match for PM confirmation. PM reviews in the dashboard: "Is feedback from john@acmecorp.io the same as Acme Corporation in your customer list?" PM confirms or rejects, and the mapping is saved permanently.

---

## New Dependencies

No new Python packages needed. This phase uses existing tools: SQLAlchemy, the LLM service from Phase 3, and standard string matching.

---

## Database Changes

### New Table: customers

The PM's customer list. One record per customer per organization.

| Column | Type | Rules |
|--------|------|-------|
| id | UUID (PK) | Auto-generated |
| org_id | UUID (FK to organizations) | Required, indexed |
| domain | string, max 255 | Required. Primary matching key. Lowercase, no www prefix. |
| company_name | string, max 255 | Nullable. Display name. |
| segment | string (enum: smb, mid_market, enterprise) | Nullable. Customer tier. |
| metadata | JSONB | Nullable. Extra fields from the PM's CSV (ARR, plan, etc.) that we store but don't use yet. |
| is_active | boolean | Default true |
| created_at | timestamptz | Auto-generated |
| updated_at | timestamptz | Auto-generated |

**Indexes:** (org_id, domain) unique composite — one domain per customer per org. org_id index.

**Important:** Domain is stored normalized — lowercase, stripped of "www." prefix, stripped of protocol. For example, "WWW.Acme.com" becomes "acme.com".

### New Table: domain_mappings

Learned mappings from source domains to customer records. This is how the system remembers past matches and never asks the same question twice.

| Column | Type | Rules |
|--------|------|-------|
| id | UUID (PK) | Auto-generated |
| org_id | UUID (FK to organizations) | Required, indexed |
| source_domain | string | Required. The domain extracted from feedback author_email. |
| source_company_name | string | Nullable. The company name from the feedback source. |
| customer_id | UUID (FK to customers) | Nullable. The matched customer. Null if confirmed as "no match." |
| confidence | float | The confidence score when the mapping was created. |
| match_method | string (enum: exact, llm_fuzzy, manual) | How this mapping was created. |
| confirmed_by | UUID (FK to users) | Nullable. The PM who confirmed this mapping (for manual and pm_review matches). |
| confirmed_at | timestamptz | Nullable. When the PM confirmed. |
| is_confirmed | boolean | Default false. True after PM confirms or after high-confidence auto-match. |
| created_at | timestamptz | Auto-generated |
| updated_at | timestamptz | Auto-generated |

**Indexes:** (org_id, source_domain) unique composite. org_id index.

### New Table: match_review_queue

Items waiting for PM review. PM sees these in the dashboard and confirms or rejects.

| Column | Type | Rules |
|--------|------|-------|
| id | UUID (PK) | Auto-generated |
| org_id | UUID (FK to organizations) | Required, indexed |
| feedback_item_id | UUID (FK to feedback_items) | Required. The feedback item that triggered this review. |
| source_domain | string | Required. Domain extracted from the feedback. |
| source_company_name | string | Nullable. Company name from the feedback. |
| candidate_customer_id | UUID (FK to customers) | Required. The suggested customer match. |
| candidate_customer_name | string | The suggested customer's display name. |
| candidate_domain | string | The suggested customer's domain. |
| confidence | float | LLM's confidence in this match. |
| status | string (enum: pending, confirmed, rejected, skipped) | Default "pending". |
| resolved_by | UUID (FK to users) | Nullable. PM who resolved this. |
| resolved_at | timestamptz | Nullable. |
| created_at | timestamptz | Auto-generated |

**Index:** (org_id, status) composite for querying pending reviews.

### Alter Table: feedback_items

Add enrichment columns to the existing feedback_items table. New Alembic migration.

| Column | Type | Set By | Rules |
|--------|------|--------|-------|
| customer_id | UUID (FK to customers) | Layer 3 | Nullable. Matched customer. |
| customer_domain | string | Layer 3 | Nullable. Domain that was matched. |
| customer_name | string | Layer 3 | Nullable. Matched company name. |
| segment | string (enum: smb, mid_market, enterprise) | Layer 3 | Nullable. From matched customer. |
| match_method | string (enum: exact, saved_mapping, llm_fuzzy, manual, unmatched) | Layer 3 | Nullable. |
| match_confidence | float | Layer 3 | Nullable. 0.0 to 1.0. |
| match_status | string (enum: matched, auto_matched, pm_review, unmatched) | Layer 3 | Default "unmatched". |
| enriched_at | timestamptz | Layer 3 | Nullable. When enrichment completed. |

**Index:** (org_id, customer_id) for querying feedback by customer. (org_id, match_status) for querying unmatched items.

---

## Customer CSV Upload

### Endpoint: `POST /api/v1/customers/upload`

- Requires authentication.
- Accepts a CSV file.
- Required columns: domain (or website, url, email_domain).
- Optional columns: company_name (or name, company, account), segment (or tier, plan, size).
- Use the same keyword-matching column detection approach from Phase 2.
- Normalize domains: lowercase, strip "www.", strip protocol (https://), strip trailing slashes.
- Skip rows with no domain.
- Deduplicate: if a customer with the same (org_id, domain) exists, update the record instead of creating a duplicate.
- Return: count of created, updated, and skipped customers.

### Endpoint: `GET /api/v1/customers`

- Requires authentication.
- Returns paginated list of customers for the current org.
- Filterable by segment.
- Searchable by domain or company_name.

### Endpoint: `GET /api/v1/customers/{id}`

- Returns single customer with their feedback stats: total feedback count, feedback by source type, most recent feedback date.

### Endpoint: `DELETE /api/v1/customers/{id}`

- Soft delete (set is_active=false). Do not hard delete — feedback items may reference this customer.

---

## The 5-Step Smart Matching Flow

This is the core of Phase 4. When a feedback item needs enrichment, it goes through these steps in order. The first step that produces a match wins.

### Step 1: Exact Domain Match

- Extract domain from the feedback item's author_email (everything after @).
- Normalize: lowercase, strip "www."
- Look up in the customers table: WHERE org_id = X AND domain = Y AND is_active = true.
- If found: match. Set customer_id, segment, match_method="exact", match_confidence=1.0, match_status="matched".
- If not found: go to Step 2.

### Step 2: Check Saved Mappings

- Look up in domain_mappings table: WHERE org_id = X AND source_domain = Y AND is_confirmed = true.
- If found and customer_id is not null: match using the saved mapping. Set match_method="saved_mapping", match_confidence from the mapping, match_status="matched".
- If found and customer_id is null: this domain was previously confirmed as "no match." Set match_status="unmatched", match_method="saved_mapping". Skip remaining steps.
- If not found: go to Step 3.

### Step 3: LLM Fuzzy Match

- Only run this if the feedback has author_email or organization_name.
- Gather the top 5 candidate customers from the database, selected by:
  - String similarity between source domain and customer domains (use Python's difflib or similar).
  - String similarity between source company name (organization_name from feedback) and customer company names.
  - Order by combined similarity score, take top 5.
- If no candidates score above a minimum threshold (e.g., similarity > 0.3), skip to Step 5.
- Send to LLM: one call with the source info and all 5 candidates.
- LLM prompt: "Given this feedback source (domain: X, company name: Y), which of these customers is the same company? Return JSON: { match_index: number or null, confidence: 0.0-1.0 }. match_index is the 0-based index of the matching candidate, or null if none match."
- Parse and validate the response.

### Step 4: Route Based on Confidence

- If LLM returns confidence > 0.85: auto-match. Save to domain_mappings with is_confirmed=true. Set feedback match_status="auto_matched".
- If LLM returns confidence 0.5-0.85: add to match_review_queue for PM review. Set feedback match_status="pm_review". Save mapping with is_confirmed=false.
- If LLM returns confidence < 0.5 or null: no match. Go to Step 5.

### Step 5: Unmatched

- Set match_status="unmatched", match_method="unmatched".
- The feedback is still usable for clustering and analysis — it just has no customer link.
- PM can manually match it later from the review queue or feedback detail view.

---

## Enrichment Trigger

Enrichment runs automatically after extraction completes. The trigger chain is:

**Ingestion (Layer 1) → Extraction (Layer 2) → Enrichment (Layer 3)**

Modify the extraction Celery task: after extraction completes successfully for a feedback item, queue an enrichment task for that item.

### Enrichment Celery Task

`enrich_feedback_item(feedback_item_id, org_id)`

- Load the feedback item.
- If match_status is already "matched" or "auto_matched", skip (idempotency).
- If the org has no customers uploaded yet, set match_status="unmatched" and stop. Don't waste LLM calls.
- Run the 5-step smart matching flow.
- Update the feedback item with enrichment fields.
- Log: feedback_id, org_id, match_method, match_status, duration_ms.

### Batch Enrichment for Existing Items

When a PM uploads their customer list for the first time, all existing feedback items that are currently "unmatched" should be re-enriched. Queue enrichment tasks for all unmatched items in the org.

**Endpoint: `POST /api/v1/enrichment/re-enrich`**
- Requires authentication.
- Queues enrichment for all feedback items in the org that have match_status="unmatched" and extraction_status="completed".
- Returns count of items queued.
- This runs as background Celery tasks (not synchronous).

---

## PM Review Queue

### How It Works

When the LLM returns a match with confidence between 0.5 and 0.85, the match is added to a review queue. The PM sees these in the dashboard and resolves them one by one.

### Endpoints

**`GET /api/v1/review-queue`**
- Requires authentication.
- Returns pending review items for the current org. Paginated.
- Each item shows: the feedback text (truncated), the source domain/company, the suggested customer name/domain, and the confidence score.

**`POST /api/v1/review-queue/{id}/confirm`**
- PM confirms the match is correct.
- Actions: update the domain_mapping to is_confirmed=true. Update the feedback item with customer_id, segment, match_status="matched", match_method="manual". Update the review queue item status to "confirmed".
- Also: find any other feedback items with the same source_domain that are unmatched or pm_review, and apply the same customer match to them (the mapping is now confirmed, so it applies to all feedback from that domain).

**`POST /api/v1/review-queue/{id}/reject`**
- PM says this is not a match.
- Actions: save a domain_mapping with customer_id=null and is_confirmed=true (so we never suggest this pair again). Update review queue item status to "rejected". Keep feedback item as unmatched.

**`POST /api/v1/review-queue/{id}/skip`**
- PM isn't sure, wants to decide later.
- Actions: update review queue item status to "skipped". No changes to feedback or mappings.

**`POST /api/v1/review-queue/{id}/manual-match`**
- PM overrides the suggestion and picks a different customer.
- Accepts: customer_id (the PM's chosen customer).
- Actions: same as confirm but with the PM's chosen customer instead of the suggested one.

---

## LLM Fuzzy Match Details

### Prompt Design

The LLM prompt for fuzzy matching must be focused and efficient. One call per unmatched feedback item (not per candidate).

**System prompt:** You are a company identity matcher. Given a feedback source and a list of candidate customers, determine if the source belongs to any of the candidates. Respond only with valid JSON.

**User prompt contents:**
- Source domain (e.g., "acmecorp.io")
- Source company name if available (e.g., "Acme Corporation")
- Numbered list of candidates with domain and company_name
- Expected output: `{ "match_index": 0, "confidence": 0.92 }` or `{ "match_index": null, "confidence": 0.0 }`

**Rules:**
- match_index is 0-based, referencing the candidate list.
- null means none of the candidates match.
- confidence is between 0.0 and 1.0.

### Batching for Bulk

When processing a CSV batch with many unmatched items, many may share the same source domain. Optimize:
- Group unmatched items by source_domain.
- Run the LLM fuzzy match once per unique source_domain (not once per feedback item).
- Apply the resulting mapping to all feedback items with that domain.

This prevents the scenario where 50 feedback items from "acmecorp.io" trigger 50 identical LLM calls.

---

## Services

### customer_service.py

Functions:
- `upload_customers_csv(db, org_id, file)` — Parse CSV, detect columns, normalize domains, create/update customers. Return counts (created, updated, skipped).
- `get_customers(db, org_id, page, page_size, segment_filter, search)` — List with pagination, optional filter and search.
- `get_customer(db, org_id, customer_id)` — Single customer with feedback stats.
- `deactivate_customer(db, org_id, customer_id)` — Soft delete.
- `normalize_domain(raw)` — Lowercase, strip www., strip protocol, strip trailing slash. Static utility.

### enrichment_service.py

Functions:
- `enrich_feedback_item(db, org_id, feedback_item_id)` — Run the 5-step smart matching flow. Return the updated feedback item.
- `extract_domain_from_email(email)` — Get domain part from an email address.
- `find_candidate_customers(db, org_id, source_domain, source_company_name, limit)` — Find top N candidates by string similarity.
- `llm_fuzzy_match(source_domain, source_company_name, candidates)` — Call LLM with fuzzy match prompt, parse and validate response.
- `apply_match(db, feedback_item, customer, method, confidence)` — Set all enrichment fields on the feedback item.
- `save_mapping(db, org_id, source_domain, source_company_name, customer_id, confidence, method, confirmed)` — Create or update domain_mapping.
- `queue_for_review(db, org_id, feedback_item, candidate_customer, confidence)` — Create match_review_queue entry.
- `re_enrich_unmatched(db, org_id)` — Queue enrichment tasks for all unmatched items. Return count.

### review_service.py

Functions:
- `get_pending_reviews(db, org_id, page, page_size)` — List pending review items.
- `confirm_review(db, org_id, review_id, user_id)` — Confirm the suggested match. Apply to feedback and all same-domain items.
- `reject_review(db, org_id, review_id, user_id)` — Reject. Save negative mapping.
- `skip_review(db, org_id, review_id)` — Mark as skipped.
- `manual_match_review(db, org_id, review_id, customer_id, user_id)` — Override with PM's choice.
- `get_review_count(db, org_id)` — Count of pending reviews (for badge in UI).

---

## Tasks (Celery)

### tasks/enrichment_tasks.py

One task:
- `enrich_feedback_item_task(feedback_item_id, org_id)` — Call enrichment_service.enrich_feedback_item. Handle errors gracefully.

### Modify Existing Tasks

**tasks/extraction_tasks.py** — After extraction completes successfully, queue `enrich_feedback_item_task` for the same item.

---

## Schemas (Pydantic)

### schemas/customer.py

- `CustomerUploadResponse` — counts: created, updated, skipped.
- `CustomerResponse` — All fields from customers table.
- `CustomerDetailResponse` — Customer fields + feedback_count, feedback_by_source, latest_feedback_date.
- `CustomerListResponse` — Paginated list.

### schemas/enrichment.py

- `ReEnrichResponse` — items_queued count.

### schemas/review.py

- `ReviewQueueItemResponse` — All review queue fields + feedback content (truncated), source info, candidate info.
- `ReviewQueueListResponse` — Paginated list.
- `ManualMatchRequest` — customer_id (UUID).

### schemas/feedback.py (update existing)

- Update `FeedbackItemResponse` to include all new enrichment fields (customer_id, segment, match_method, match_status, etc.).

---

## Models (SQLAlchemy)

Create new model files:

- `backend/app/models/customer.py` — Customer model.
- `backend/app/models/domain_mapping.py` — DomainMapping model.
- `backend/app/models/match_review.py` — MatchReviewQueue model.

Update existing:

- `backend/app/models/feedback_item.py` — Add enrichment columns.

Update models `__init__.py` to export new models.

---

## Alembic Migrations

Two migrations:

**`005_create_customers_domain_mappings_match_reviews`** — Create all three new tables with indexes and foreign keys.

**`006_add_enrichment_fields_to_feedback_items`** — Add enrichment columns to feedback_items. All new columns must be nullable.

---

## API Endpoints Summary

### Customers

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/v1/customers/upload | Yes | Upload customer CSV |
| GET | /api/v1/customers | Yes | List customers (paginated, filterable, searchable) |
| GET | /api/v1/customers/{id} | Yes | Get customer with feedback stats |
| DELETE | /api/v1/customers/{id} | Yes | Soft delete customer |

### Enrichment

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/v1/enrichment/re-enrich | Yes | Re-enrich all unmatched feedback items |

### Review Queue

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/v1/review-queue | Yes | List pending review items |
| POST | /api/v1/review-queue/{id}/confirm | Yes | Confirm suggested match |
| POST | /api/v1/review-queue/{id}/reject | Yes | Reject suggested match |
| POST | /api/v1/review-queue/{id}/skip | Yes | Skip (decide later) |
| POST | /api/v1/review-queue/{id}/manual-match | Yes | Override with PM's choice |

---

## Frontend Changes

### Customer Management (new section in Settings or separate page)

**Customer Upload:**
- Section on Settings page (or separate Customers page accessible from sidebar).
- Drag-and-drop or file select for customer CSV.
- After upload: show summary — "Created 145 customers, updated 12, skipped 3."
- Explain: "Upload a CSV with at least a 'domain' column. Optional: company_name, segment."

**Customer List:**
- Table showing: domain, company name, segment, feedback count.
- Filter by segment (All, SMB, Mid-Market, Enterprise).
- Search by domain or company name.
- Click a customer to see their feedback items.

### Review Queue (new component/page)

**Location:** A notification badge on the sidebar showing pending review count. Clicking it opens the review queue.

**Review Queue UI:**
- List of pending matches.
- Each item shows:
  - The feedback text (truncated, first 100 chars).
  - Source: "john@acmecorp.io" or "Acme Corporation"
  - Suggested match: "Acme Inc (acme.com) — Enterprise"
  - Confidence score (e.g., "72% confident")
  - Three buttons: Confirm, Reject, Skip
  - A "Choose different customer" option that opens a customer search/select dropdown.
- After resolving an item, it disappears from the queue and the next one shows.
- When queue is empty: "All caught up! No matches to review."

### Feedback List (update)

- Add a customer column/badge showing the matched customer name and segment.
- Unmatched items show "No customer" in gray.
- Items in PM review show "Pending review" badge.
- Filter by: segment (All, SMB, Mid-Market, Enterprise, Unmatched).
- Filter by: match status (All, Matched, Pending Review, Unmatched).

### Feedback Detail (update)

- Show matched customer info: company name, domain, segment.
- If unmatched: show a "Match to customer" button that lets PM manually select a customer.
- If pm_review: show the pending review inline with confirm/reject options.

### Sidebar Updates

- Add "Customers" link (if separate page) or make it accessible from Settings.
- Add review queue badge with pending count (e.g., a red circle with "5" next to an icon).

### Dashboard Updates

- Add enrichment stats: "Matched: 120, Pending Review: 5, Unmatched: 23"
- Add top customers card: top 5 customers by feedback count.

---

## Testing

### test_customer_service.py
1. Upload customer CSV with valid data — customers created with normalized domains.
2. Upload with duplicate domains — existing customers updated, not duplicated.
3. Domain normalization: "WWW.Acme.COM" becomes "acme.com", "https://www.example.org/" becomes "example.org".
4. Get customers filters by org_id (multi-tenant isolation).
5. Search customers by domain or name works.
6. Deactivate customer sets is_active=false.
7. Customer from another org is not accessible.

### test_enrichment_service.py
1. Feedback with exact domain match — matched instantly, no LLM call.
2. Feedback with saved mapping — matched using saved mapping, no LLM call.
3. Feedback with negative saved mapping (customer_id=null) — correctly set to unmatched, no LLM call.
4. Feedback with no matching domain — LLM fuzzy match triggered.
5. LLM returns confidence > 0.85 — auto-matched, mapping saved.
6. LLM returns confidence 0.5-0.85 — queued for PM review.
7. LLM returns confidence < 0.5 — set to unmatched.
8. Feedback with no author_email — skip LLM, set to unmatched.
9. Org with no customers — all feedback set to unmatched, no LLM calls.
10. Already matched feedback — skipped (idempotency).
11. Items with same source domain are grouped — LLM called once, not per item.

### test_review_service.py
1. Confirm review — feedback gets customer, mapping saved as confirmed, other same-domain items also matched.
2. Reject review — negative mapping saved, feedback stays unmatched.
3. Skip review — status changed, no other effects.
4. Manual match — feedback gets PM's chosen customer, mapping saved.
5. Review queue filters by org_id.
6. Pending count is accurate.

### test_customer_routes.py
1. POST /customers/upload with valid CSV returns correct counts.
2. GET /customers returns paginated list for current org only.
3. GET /customers with segment filter works.
4. GET /customers with search works.
5. GET /customers/{id} returns customer with feedback stats.
6. DELETE /customers/{id} soft deletes.
7. Customer from another org not accessible.

### test_enrichment_routes.py
1. POST /enrichment/re-enrich queues tasks for unmatched items.
2. GET /feedback shows enrichment fields when matched.
3. Feedback from another org not accessible.

### test_review_routes.py
1. GET /review-queue returns pending items for current org.
2. POST confirm updates feedback and mapping correctly.
3. POST reject saves negative mapping.
4. Review items from another org not accessible.

---

## Non-Negotiable Rules for This Phase

Everything from Phases 1-3 still applies, plus:

1. **Domain normalization is consistent everywhere.** The same function normalizes domains in customer upload, email extraction, and mapping lookups. Define it once, use it everywhere.
2. **Saved mappings prevent redundant LLM calls.** If a domain has been matched before (confirmed or rejected), the LLM is never called for that domain again.
3. **LLM calls are grouped by source domain.** If 50 feedback items share a domain, the LLM is called once, not 50 times.
4. **PM review confirmations cascade.** When PM confirms "acmecorp.io = Acme Inc", ALL feedback from acmecorp.io gets matched, not just the one reviewed.
5. **Enrichment is idempotent.** Running enrichment twice on matched feedback does nothing.
6. **Customer queries filter by org_id.** A PM never sees another org's customers.
7. **Enrichment never blocks ingestion or extraction.** If enrichment fails for one item, others continue.
8. **Tokens are never logged.** Slack tokens from Phase 2 and any API keys must stay out of logs.

---

## What NOT to Build

- Embeddings or vector storage (Phase 5)
- Clustering or theme creation (Phase 5)
- Scoring or prioritization (Phase 5)
- Chat functionality (Phase 6)
- Brief generation (Phase 7)
- Solution design (Phase 7)
- Spec generation (Phase 8)
- Stripe/HubSpot integrations for customer data (future, not in any current phase)

---

## Acceptance Criteria

Phase 4 is complete when ALL of these are true:

- [ ] PM can upload a customer CSV and see customers created with normalized domains
- [ ] Duplicate customer domains are updated, not duplicated
- [ ] Customer list is paginated, filterable by segment, and searchable
- [ ] Customer detail shows feedback stats
- [ ] New feedback with an exact domain match is auto-matched (match_method="exact", confidence=1.0)
- [ ] New feedback matching a saved mapping is matched without LLM call
- [ ] New feedback with no exact match triggers LLM fuzzy matching (one call per unique domain, not per item)
- [ ] High-confidence LLM matches (>0.85) are auto-matched and mapping is saved
- [ ] Medium-confidence matches (0.5-0.85) appear in the PM review queue
- [ ] Low-confidence matches (<0.5) are set to unmatched
- [ ] PM can confirm a review — feedback is matched, mapping is saved, same-domain items are also matched
- [ ] PM can reject a review — negative mapping saved, domain never suggested again
- [ ] PM can skip a review — no changes, can revisit later
- [ ] PM can override with a different customer (manual-match)
- [ ] Review queue badge shows pending count in sidebar
- [ ] Uploading customers for the first time triggers re-enrichment of existing unmatched feedback
- [ ] Feedback list shows customer name, segment, and match status
- [ ] Feedback list is filterable by segment and match status
- [ ] Feedback detail shows matched customer info or "Match to customer" button if unmatched
- [ ] Dashboard shows enrichment stats and top customers
- [ ] Enrichment is idempotent (already matched items are skipped)
- [ ] Enrichment continues even if one item fails
- [ ] All Phase 4 tests pass
- [ ] All Phase 1, 2, and 3 tests still pass

---

## How to Give This to Cursor

1. Save this file as `D:\LinkedIn\Week4\docs\PHASE_4_SPEC.md`
2. Open Cursor's chat and type:

> Read `docs/PHASE_4_SPEC.md`. This is the spec for Phase 4. The `.cursorrules` file still applies. Do NOT start building yet. Create a detailed implementation plan first: list every file you will create or modify, what each contains, the order of work, and dependencies. Present the full plan and wait for my approval.

3. Review the plan. Approve or push back.
4. Let Cursor build.
5. Run through acceptance criteria.

---

## After Phase 4

Once all acceptance criteria pass, come back for Phase 5: Clustering & Prioritization. That phase will add:
- Embedding generation (all-MiniLM-L6-v2 via sentence-transformers)
- pgvector storage for embeddings
- HDBSCAN clustering into themes
- Theme naming via LLM
- Aggregate stats per theme (mention count, segment breakdown, urgency breakdown)
- PM scoring settings (goals, target segments, weights)
- 5-factor prioritization engine
- Ranked theme list in the dashboard
