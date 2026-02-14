# Phase 4: Customer Enrichment — Verification Checklist

> Run through this checklist yourself AFTER Cursor says Phase 4 is complete.
> Every item must pass before moving to Phase 5.

---

## Docker & Infrastructure

- [ ] `docker-compose up --build` starts all services without errors
- [ ] All Phase 1, 2, and 3 tests still pass
- [ ] Run: `docker-compose exec backend pytest app/tests/ -v`

---

## Customer CSV Upload

- [ ] Create a test CSV with columns: domain, company_name, segment. Add 10-15 rows.
- [ ] Upload through the frontend — see summary: "Created X, Updated Y, Skipped Z"
- [ ] Check customer list — all customers appear with correct data
- [ ] Domains are normalized (e.g., "WWW.Acme.COM" shows as "acme.com", "https://example.org/" shows as "example.org")
- [ ] Upload the same CSV again — no duplicates, existing records updated
- [ ] Upload a CSV with no "domain" column — get a clear error
- [ ] Upload a CSV with some rows missing domain — those rows skipped, others processed

---

## Customer List

- [ ] Customer list shows: domain, company name, segment, feedback count
- [ ] Pagination works
- [ ] Filter by segment works (All, SMB, Mid-Market, Enterprise)
- [ ] Search by domain works
- [ ] Search by company name works
- [ ] Click a customer — see their detail page with feedback stats (total count, by source, latest date)
- [ ] Only YOUR org's customers show (not another org's)

---

## Customer Delete

- [ ] Delete a customer — they disappear from the list
- [ ] Check the database: is_active is false (soft delete, not hard delete)
- [ ] Feedback items that referenced this customer are NOT deleted

---

## Exact Domain Match (Step 1)

- [ ] Upload customers with domain "acme.com"
- [ ] Submit manual feedback with author_email "john@acme.com"
- [ ] Wait for extraction + enrichment to complete
- [ ] Check the feedback item: customer matched, match_method="exact", confidence=1.0, match_status="matched"
- [ ] Customer name and segment are filled in on the feedback item

---

## Saved Mapping Match (Step 2)

- [ ] After the exact match above, submit another feedback from "jane@acme.com"
- [ ] This should match instantly via saved mapping (no LLM call needed)
- [ ] Check: match_method="saved_mapping" or "exact" (same domain, should be instant)

---

## LLM Fuzzy Match (Step 3)

- [ ] Upload a customer with domain "acme-corp.com", company name "Acme Corporation"
- [ ] Submit feedback with author_email "support@acmecorp.io" (similar but not exact)
- [ ] Wait for enrichment — the LLM should attempt fuzzy matching
- [ ] Check the result: either auto-matched (high confidence) or queued for PM review (medium confidence)

---

## PM Review Queue (Step 4)

- [ ] If fuzzy match produced a medium-confidence match, check the review queue
- [ ] Review queue shows: feedback text (truncated), source domain, suggested customer, confidence score
- [ ] Sidebar shows a badge with pending review count
- [ ] **Confirm** a match:
  - [ ] Feedback item gets the customer assigned
  - [ ] Mapping is saved
  - [ ] Other feedback from the same domain is also matched automatically
- [ ] **Reject** a match:
  - [ ] Feedback stays unmatched
  - [ ] Negative mapping saved (this pair never suggested again)
  - [ ] Submit new feedback from the same rejected domain — it goes straight to unmatched (no LLM call)
- [ ] **Skip** a match:
  - [ ] Item moves out of queue but no permanent changes
  - [ ] Can revisit later
- [ ] **Manual match** (choose different customer):
  - [ ] Pick a different customer from a dropdown/search
  - [ ] Feedback gets the PM's chosen customer
  - [ ] Mapping saved for that domain → customer pair

---

## Unmatched Feedback (Step 5)

- [ ] Submit feedback with author_email from a completely unknown domain (e.g., "random@xyznotexist123.com")
- [ ] No customers match, no similar domains
- [ ] Feedback shows match_status="unmatched"
- [ ] Feedback is still visible in the list and still has extraction fields

---

## Re-enrichment

- [ ] Start with an org that has feedback but NO customers uploaded yet
- [ ] All feedback should be "unmatched"
- [ ] Upload a customer CSV
- [ ] Trigger re-enrichment (POST /api/v1/enrichment/re-enrich or via UI)
- [ ] Wait for background processing
- [ ] Previously unmatched feedback with matching domains now shows as "matched"

---

## LLM Call Optimization

- [ ] Upload a CSV with 20 feedback items all from "support@acmecorp.io"
- [ ] Check backend logs: the LLM fuzzy match should be called ONCE for "acmecorp.io", not 20 times
- [ ] All 20 items get the same match result

---

## Feedback List Updates

- [ ] Feedback list shows a customer column (company name + segment)
- [ ] Unmatched items show "No customer" in gray
- [ ] Items in PM review show "Pending review" badge
- [ ] Filter by segment works (All, SMB, Mid-Market, Enterprise, Unmatched)
- [ ] Filter by match status works (All, Matched, Pending Review, Unmatched)

---

## Feedback Detail Updates

- [ ] Matched feedback shows: customer name, domain, segment
- [ ] Unmatched feedback shows a "Match to customer" button
- [ ] Clicking "Match to customer" lets PM search and select a customer manually
- [ ] PM review feedback shows the pending review inline with confirm/reject

---

## Dashboard Updates

- [ ] Dashboard shows enrichment stats: "Matched: X, Pending Review: Y, Unmatched: Z"
- [ ] Dashboard shows top 5 customers by feedback count

---

## Multi-Tenant Isolation

- [ ] Create a second org (sign up with different email)
- [ ] Upload different customers to the second org
- [ ] Verify: first org cannot see second org's customers
- [ ] Verify: first org's feedback is not matched to second org's customers
- [ ] Verify: review queue only shows current org's items

---

## Idempotency

- [ ] Trigger enrichment on an already-matched feedback item
- [ ] Nothing changes — it's skipped (not re-processed)
- [ ] No duplicate LLM calls in the logs

---

## Error Handling

- [ ] If LLM is down during enrichment, the feedback item is NOT stuck
- [ ] Enrichment failure for one item does not block others
- [ ] Failed enrichments can be retried later via re-enrich

---

## Quick API Spot Checks

Open `http://localhost:8000/docs` and test:

- [ ] `POST /api/v1/customers/upload` — uploads customer CSV
- [ ] `GET /api/v1/customers` — returns paginated customer list
- [ ] `GET /api/v1/customers/{id}` — returns customer with feedback stats
- [ ] `DELETE /api/v1/customers/{id}` — soft deletes
- [ ] `POST /api/v1/enrichment/re-enrich` — returns items queued count
- [ ] `GET /api/v1/review-queue` — returns pending reviews
- [ ] `POST /api/v1/review-queue/{id}/confirm` — confirms match
- [ ] `POST /api/v1/review-queue/{id}/reject` — rejects match
- [ ] All error responses follow: `{ "error": { "code": "...", "message": "..." } }`

---

## Tests

- [ ] All Phase 4 backend tests pass
- [ ] All Phase 3 backend tests still pass
- [ ] All Phase 2 backend tests still pass
- [ ] All Phase 1 backend tests still pass
- [ ] Run: `docker-compose exec backend pytest app/tests/ -v`

---

## If Something Fails

Tell Cursor: "Phase 4 checklist item [X] failed. Here's what happened: [describe]. Fix it following the spec in docs/PHASE_4_SPEC.md."

Once everything passes, move to Phase 5.
