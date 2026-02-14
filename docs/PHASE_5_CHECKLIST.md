# Phase 5: Clustering & Prioritization — Verification Checklist

> Run through this checklist yourself AFTER Cursor says Phase 5 is complete.
> Every item must pass before moving to Phase 6.
> 
> **This is the core value phase. Test it thoroughly.**

---

## Docker & Infrastructure

- [ ] `docker-compose up --build` starts all services without errors
- [ ] All Phase 1-4 tests still pass
- [ ] Run: `docker-compose exec backend pytest app/tests/ -v`

---

## Embedding Generation

- [ ] Submit a new manual feedback item with a clear pain point
- [ ] Wait for extraction + enrichment + embedding to complete
- [ ] Check the database: the feedback item has a non-null embedding (384 dimensions)
- [ ] Check backend logs: embedding model loaded ONCE at startup (not per item)
- [ ] Submit 5 more feedback items — all get embeddings
- [ ] Items where extraction failed (no pain_point) do NOT get embeddings — no crash

---

## Clustering — Manual Trigger

- [ ] Make sure you have at least 20-30 feedback items with embeddings (upload a CSV if needed)
- [ ] Include items with 3-4 distinct topics (e.g., 10 about "SSO/authentication", 8 about "search performance", 7 about "mobile app crashes")
- [ ] Click "Re-cluster" or trigger `POST /api/v1/clustering/run`
- [ ] Clustering starts as a background task (API returns immediately)
- [ ] Check clustering status — shows "running" then "completed"
- [ ] Themes appear in the Theme Dashboard

---

## Clustering — Quality Check

- [ ] Feedback about "SSO/authentication" is grouped into one theme
- [ ] Feedback about "search performance" is grouped into a different theme
- [ ] Feedback about "mobile crashes" is in its own theme
- [ ] Themes are NOT just random groupings — similar feedback is actually together
- [ ] Each theme has an LLM-generated name that makes sense (not "Theme 1")
- [ ] Each theme has a 2-3 sentence description that accurately summarizes the feedback

---

## Clustering — Automatic Trigger

- [ ] Check the RECLUSTER_THRESHOLD value (default 50)
- [ ] Upload enough new feedback items to cross the threshold (items with embeddings but no theme)
- [ ] Clustering triggers automatically in the background
- [ ] New themes appear without manual intervention

---

## Outliers

- [ ] Some feedback items that don't fit any cluster are marked as outliers
- [ ] Outliers are accessible via "Outliers" section in the UI
- [ ] Outliers are NOT hidden — PM can see them
- [ ] Outliers still have their extraction and enrichment data intact

---

## Historical Themes

- [ ] Note the current themes and their IDs
- [ ] Trigger re-clustering
- [ ] Old themes are marked is_current=false (not deleted)
- [ ] New themes appear with is_current=true
- [ ] The Theme Dashboard only shows current themes
- [ ] Old themes still exist in the database for historical reference

---

## Theme Stats

For each theme, verify:

- [ ] **Mention count** matches the actual number of feedback items in the theme
- [ ] **Unique customers** is correct (not just total items — distinct customers)
- [ ] **Segment breakdown** is correct (e.g., { "enterprise": 12, "mid_market": 5 })
- [ ] **Urgency breakdown** is correct (e.g., { "critical": 4, "high": 8, "medium": 6, "low": 2 })
- [ ] **Sentiment breakdown** is correct
- [ ] **Top quotes** are actual verbatim quotes from feedback items in this theme (not hallucinated)

---

## Scoring Configuration

- [ ] Go to Settings → Scoring section
- [ ] See 5 weight sliders: Volume, Reach, Urgency, Sentiment, Strategic Fit
- [ ] Sliders default to: 25%, 20%, 25%, 15%, 15%
- [ ] Adjust one slider — others auto-adjust so total stays at 100%
- [ ] Add product goals (e.g., "Improve enterprise retention")
- [ ] Select target segments (e.g., Enterprise, Mid-Market)
- [ ] Click Apply/Save
- [ ] Check: weights sum validation works — cannot save if sum ≠ 100%
- [ ] "Reset to defaults" button works

---

## Priority Scores

- [ ] Every theme has a priority score (not null)
- [ ] Theme Dashboard shows themes ranked by score (highest first)
- [ ] The #1 theme is not random — it has high volume + urgency + sentiment + fit

### Score Breakdown Verification

Pick a theme and check its score breakdown:

- [ ] **Volume:** The theme with the most mentions should have volume close to 1.0
- [ ] **Reach:** The theme with the most diverse customers should have reach close to 1.0
- [ ] **Urgency:** A theme where most items are "critical" or "high" should score high
- [ ] **Sentiment:** A theme where most items are "negative" should score high
- [ ] **Strategic Fit:** A theme about "enterprise auth" should score high if PM's goal is "Improve enterprise retention"
- [ ] **Final score** = weighted sum of all factors (manually verify the math on one theme)
- [ ] Score breakdown shows raw, normalized, and weighted values for each factor

---

## Scoring — Weight Changes

- [ ] Note the current theme rankings
- [ ] Go to Settings and change weights (e.g., set Urgency to 50%, reduce others)
- [ ] Apply changes
- [ ] Theme rankings change (themes with high urgency move up)
- [ ] Score breakdowns update with new weights
- [ ] No re-clustering needed — only re-scoring happens

---

## Scoring — Goal Changes

- [ ] Change product goals (e.g., from "enterprise retention" to "reduce onboarding friction")
- [ ] Apply changes
- [ ] Strategic fit scores change for themes
- [ ] Overall rankings may shift based on new goal alignment

---

## Theme Dashboard (Main Page)

- [ ] Shows ranked theme cards, highest score first
- [ ] Each card shows:
  - [ ] Rank number (#1, #2, etc.)
  - [ ] Theme name (bold)
  - [ ] Priority score (prominent number)
  - [ ] Score breakdown (visual bar or chart showing 5 factors)
  - [ ] Mention count
  - [ ] Unique customer count
  - [ ] Segment pills with counts (Enterprise, Mid-Market, SMB)
  - [ ] Urgency breakdown (visual)
  - [ ] Top 2 verbatim quotes
- [ ] Click a theme card → goes to Theme Detail page

---

## Theme Detail Page

- [ ] Shows theme name and description
- [ ] Full score breakdown with each factor's raw, normalized, and weighted values
- [ ] "Why this score" explanation in plain language
- [ ] Segment breakdown chart
- [ ] Urgency breakdown chart
- [ ] Sentiment breakdown chart
- [ ] Paginated list of all feedback items in this theme
- [ ] Each item shows: content, author, source, urgency, customer name
- [ ] Top quotes highlighted

---

## Dashboard Updates

- [ ] Dashboard shows "Top 5 Priorities" card with theme names and scores
- [ ] Dashboard shows "Clustering Status": last run time, clusters found, outliers, pending items

---

## Feedback List Updates

- [ ] Each feedback item shows its theme name (or "Outlier" or "Unclustered")
- [ ] Filter by theme works (dropdown of current theme names)
- [ ] Click a theme name → goes to theme detail page

---

## Sidebar

- [ ] "Priorities" is the top link in the sidebar
- [ ] Sidebar order: Priorities, Feedback, Customers, Settings
- [ ] "Priorities" links to the Theme Dashboard

---

## Multi-Tenant Isolation

- [ ] Create a second org with different feedback
- [ ] Cluster the second org separately
- [ ] First org cannot see second org's themes
- [ ] First org's scoring config is independent from second org's
- [ ] Theme IDs from one org return 404 when accessed by another org

---

## Performance

- [ ] Embedding generation is fast (~50ms per item, check logs)
- [ ] Clustering 200+ items completes within a reasonable time (under 2 minutes)
- [ ] Theme Dashboard loads quickly (under 2 seconds)
- [ ] Similarity searches work (theme detail page loads related items)

---

## Error Handling

- [ ] If LLM is down during theme naming, themes still get created with fallback names ("Theme 1", "Theme 2")
- [ ] If LLM is down during strategic fit scoring, strategic_fit defaults to 0.5
- [ ] Clustering failure doesn't crash the app
- [ ] Embedding failure for one item doesn't block others

---

## Quick API Spot Checks

Open `http://localhost:8000/docs` and test:

- [ ] `GET /api/v1/themes` — returns ranked themes
- [ ] `GET /api/v1/themes/{id}` — returns theme detail
- [ ] `GET /api/v1/themes/{id}/feedback` — returns paginated feedback in theme
- [ ] `GET /api/v1/themes/outliers` — returns unclustered items
- [ ] `POST /api/v1/clustering/run` — triggers clustering
- [ ] `GET /api/v1/clustering/status` — returns status
- [ ] `GET /api/v1/scoring/config` — returns scoring config
- [ ] `PATCH /api/v1/scoring/config` — updates config, triggers re-scoring
- [ ] `POST /api/v1/scoring/re-score` — re-scores without re-clustering
- [ ] All error responses follow: `{ "error": { "code": "...", "message": "..." } }`

---

## Tests

- [ ] All Phase 5 backend tests pass
- [ ] All Phase 4 backend tests still pass
- [ ] All Phase 3 backend tests still pass
- [ ] All Phase 2 backend tests still pass
- [ ] All Phase 1 backend tests still pass
- [ ] Run: `docker-compose exec backend pytest app/tests/ -v`

---

## The "Does It Feel Right?" Test

This is the most important test. Forget the checkboxes for a moment:

1. Upload 50+ real or realistic feedback items spanning 3-5 topics.
2. Trigger clustering.
3. Look at the Theme Dashboard.
4. **Does it make sense?** Are the themes sensible groupings? Are the names accurate? Is the #1 priority something you'd actually agree with?
5. **Change the weights.** Do the rankings change in a way that makes intuitive sense?
6. **Click into a theme.** Can you understand why it's ranked there? Does the evidence (quotes, stats, breakdown) support the score?

If you can look at the Theme Dashboard and think "Yes, this is telling me something useful about what to build next" — Phase 5 is done.

---

## If Something Fails

Tell Cursor: "Phase 5 checklist item [X] failed. Here's what happened: [describe]. Fix it following the spec in docs/PHASE_5_SPEC.md."

Once everything passes, move to Phase 6.
