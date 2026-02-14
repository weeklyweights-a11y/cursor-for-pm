# Phase 5: Clustering & Prioritization

> **Goal:** Feedback items with similar pain points are automatically grouped into themes. Each theme gets a name, description, and aggregate stats. PMs configure their priorities (goals, target segments, weights), and the system scores every theme with a transparent 5-factor formula. The dashboard shows a ranked list: "Here's what to build next, and here's the evidence."
>
> **Done means:** A PM with 200+ feedback items sees them automatically clustered into 10-20 themes. Each theme has a name ("SSO & Enterprise Auth"), mention count, segment breakdown, and urgency distribution. The PM has configured their scoring weights, and every theme has a priority score with a clear explanation of why. The dashboard shows a ranked theme list that answers: "What should I build next?"

---

## Context for the AI Agent

This is Phase 5 of 8. Phases 1-4 are complete — you have authentication, feedback ingestion, LLM extraction (pain points, urgency, sentiment, topics), customer enrichment with smart matching, and a working PM review queue.

**This is the most important phase of the product.** Everything before this was plumbing. This phase delivers the core value proposition: turning scattered feedback into ranked, evidence-backed priorities. If this phase works well, PMs will pay for the product.

Read `.cursorrules` before starting. All rules apply.

**Project root:** `D:\LinkedIn\Week4`

---

## What You Are Building

Four things:

1. **Embedding generation** — Convert every feedback item's pain_point into a vector using a sentence transformer model. Store vectors in pgvector.

2. **Clustering** — Group similar feedback items by their embedding vectors using HDBSCAN. Each cluster becomes a theme.

3. **Theme management** — LLM names each cluster, generates a description, and computes aggregate stats (mention count, segment breakdown, urgency breakdown, top quotes).

4. **Prioritization engine** — A 5-factor scoring formula that ranks themes. PMs configure the weights. Every score is explainable.

---

## New Dependencies

| Package | Purpose |
|---------|---------|
| sentence-transformers | Generate text embeddings using all-MiniLM-L6-v2 model |
| hdbscan | Density-based clustering algorithm |
| numpy | Numerical operations for vectors and scoring |
| scikit-learn | Cosine similarity calculations, optional preprocessing |

---

## Docker Compose Changes

No new services needed. The sentence-transformers model runs inside the existing worker and backend containers (CPU is fine — all-MiniLM-L6-v2 is tiny and fast, ~50ms per embedding on CPU).

**New environment variables:**

| Variable | Dev Value | Purpose |
|----------|-----------|---------|
| EMBEDDING_MODEL | all-MiniLM-L6-v2 | Sentence transformer model name |
| EMBEDDING_DIMENSION | 384 | Vector dimension for pgvector column |
| HDBSCAN_MIN_CLUSTER_SIZE | 3 | Minimum feedback items to form a cluster |
| HDBSCAN_MIN_SAMPLES | 2 | Density parameter for HDBSCAN |
| RECLUSTER_THRESHOLD | 50 | Re-cluster when this many new un-clustered items accumulate |

---

## Database Changes

### Alter Table: feedback_items

Add embedding and cluster columns. New Alembic migration.

| Column | Type | Set By | Rules |
|--------|------|--------|-------|
| embedding | vector(384) | Layer 4 | Nullable. pgvector column. The pain_point embedding. |
| theme_id | UUID (FK to themes) | Layer 4 | Nullable. Which theme this item belongs to. |
| is_outlier | boolean | Layer 4 | Default false. True if HDBSCAN classified this as noise. |
| clustered_at | timestamptz | Layer 4 | Nullable. When this item was last assigned to a cluster. |

**Index:** Create an IVFFlat or HNSW index on the embedding column for fast similarity search. Use HNSW with cosine distance.

### New Table: themes

Each cluster becomes a theme. This is what PMs interact with.

| Column | Type | Rules |
|--------|------|-------|
| id | UUID (PK) | Auto-generated |
| org_id | UUID (FK to organizations) | Required, indexed |
| name | string, max 255 | Required. LLM-generated name (e.g., "SSO & Enterprise Authentication"). |
| description | text | Required. LLM-generated 2-3 sentence summary. |
| centroid | vector(384) | Required. Average embedding of all items in this cluster. |
| mention_count | integer | Required. Number of feedback items in this theme. |
| unique_customers | integer | Default 0. Number of distinct customers mentioning this theme. |
| segment_breakdown | JSONB | Default {}. e.g., { "enterprise": 12, "mid_market": 5, "smb": 3 } |
| urgency_breakdown | JSONB | Default {}. e.g., { "critical": 4, "high": 8, "medium": 6, "low": 2 } |
| sentiment_breakdown | JSONB | Default {}. e.g., { "negative": 15, "neutral": 3, "positive": 2 } |
| top_quotes | JSONB | Default []. Top 5 most representative verbatim_quotes from items. |
| priority_score | float | Nullable. Calculated by the prioritization engine. |
| score_breakdown | JSONB | Nullable. e.g., { "volume": 0.8, "reach": 0.7, "urgency": 0.9, "sentiment": 0.6, "strategic_fit": 0.75, "weights_used": {...} } |
| is_current | boolean | Default true. False for themes from previous clustering runs (historical). |
| created_at | timestamptz | Auto-generated |
| updated_at | timestamptz | Auto-generated |

**Indexes:** org_id, (org_id, is_current) composite, priority_score for sorting.

### New Table: scoring_configs

PM's prioritization preferences. One per organization.

| Column | Type | Rules |
|--------|------|-------|
| id | UUID (PK) | Auto-generated |
| org_id | UUID (FK to organizations) | Required, unique, indexed |
| goals | text[] | Nullable. PM's current product goals (e.g., ["Improve enterprise retention", "Reduce onboarding time"]). |
| target_segments | text[] | Nullable. Segments the PM cares most about (e.g., ["enterprise", "mid_market"]). |
| weight_volume | float | Default 0.25. How much mention count matters. |
| weight_reach | float | Default 0.20. How much customer diversity matters. |
| weight_urgency | float | Default 0.25. How much urgency matters. |
| weight_sentiment | float | Default 0.15. How much negative sentiment matters. |
| weight_strategic_fit | float | Default 0.15. How much alignment with goals matters. |
| created_at | timestamptz | Auto-generated |
| updated_at | timestamptz | Auto-generated |

**Constraint:** All 5 weights must sum to 1.0. Validate on save.

---

## Embedding Generation

### When It Runs

After extraction completes for a feedback item, if the item has a pain_point (extraction succeeded), generate an embedding. This is a new step in the pipeline:

**Ingestion → Extraction → Enrichment → Embedding**

Modify the enrichment Celery task: after enrichment completes, if the item has a pain_point and no embedding yet, generate the embedding.

### How It Works

- Use the `sentence-transformers` library with the `all-MiniLM-L6-v2` model.
- Input: the feedback item's `pain_point` text. If pain_point is empty, use the `content` field (the raw feedback).
- Output: a 384-dimensional float vector.
- Store in the feedback item's `embedding` column (pgvector).
- This model is tiny (~80MB) and fast (~50ms per embedding on CPU). No GPU needed.

### Embedding Service

Create `backend/app/services/embedding_service.py`

Functions:
- `generate_embedding(text)` — Load the model (cache it as a singleton, do not reload per call), encode the text, return the vector.
- `generate_embeddings_batch(texts)` — Batch encode multiple texts at once. Sentence-transformers supports batching natively and it's much faster than one-at-a-time.
- `get_similar_items(db, org_id, embedding, limit)` — Use pgvector's cosine distance operator to find the N most similar feedback items. Used later for theme detail views.

**Model Loading:** The sentence-transformers model should be loaded ONCE when the worker/backend starts, not per request. Use a module-level singleton or a cached function. Loading takes ~2 seconds; inference takes ~50ms.

---

## Clustering

### When It Runs

Clustering is triggered in two ways:

1. **Manual trigger:** PM clicks "Re-cluster" button in the dashboard.
2. **Automatic trigger:** When the count of feedback items with embeddings but no theme_id exceeds RECLUSTER_THRESHOLD (default 50).

Clustering always runs as a Celery background task. It processes ALL feedback items with embeddings for the org (not just new ones), because clusters can shift as new data arrives.

### How HDBSCAN Works (For the Implementation)

HDBSCAN is a density-based clustering algorithm. Unlike K-means, you don't need to specify the number of clusters in advance — it discovers them automatically.

Steps:
1. Load all feedback item embeddings for the org from the database.
2. Stack them into a numpy matrix.
3. Run HDBSCAN with min_cluster_size and min_samples from environment config.
4. HDBSCAN returns a label for each item: a cluster number (0, 1, 2...) or -1 for noise (outliers).
5. Items labeled -1 are marked as outliers (is_outlier=true, theme_id=null).
6. Items with a cluster label get assigned to a theme.

### Clustering Flow

1. Load all feedback items with embeddings for the org.
2. Run HDBSCAN on the embedding matrix.
3. Mark all existing themes for this org as is_current=false (they're now historical).
4. For each cluster:
   a. Compute the centroid (average of all embeddings in the cluster).
   b. Gather the feedback items in this cluster.
   c. Compute aggregate stats: mention_count, unique_customers, segment_breakdown, urgency_breakdown, sentiment_breakdown.
   d. Select top 5 verbatim_quotes (pick the ones closest to the centroid — most representative).
   e. Call the LLM to generate a name and description for this theme (see below).
   f. Create a new theme record with is_current=true.
   g. Update all feedback items in this cluster: theme_id = new theme, is_outlier = false, clustered_at = now.
5. Mark outlier items: theme_id=null, is_outlier=true, clustered_at=now.
6. Run the prioritization engine on all new themes (if scoring config exists).
7. Log: org_id, total items, clusters found, outliers, duration_ms.

### Theme Naming (LLM Call)

For each cluster, send the top 10 verbatim_quotes (or pain_points) to the LLM and ask it to:
- Generate a short theme name (2-5 words, e.g., "SSO & Enterprise Auth", "Search Performance Issues", "Mobile App Crashes").
- Generate a description (2-3 sentences summarizing what customers are saying).

**System prompt:** You are a product analyst. Given a set of customer feedback quotes about the same topic, generate a concise theme name and description. Respond only with JSON.

**Expected output:** `{ "name": "SSO & Enterprise Authentication", "description": "Multiple enterprise customers are blocked on deployment because the product lacks SAML/SSO integration. This is especially urgent for accounts with IT security requirements." }`

**Rules:**
- One LLM call per cluster (not per item).
- If the LLM fails, use a fallback name: "Theme {cluster_number}" and description: "Cluster of {N} related feedback items."
- Store the LLM-generated name and description on the theme record.

---

## Prioritization Engine

### The 5 Factors

Every theme is scored on 5 factors, each normalized to 0.0-1.0:

| Factor | What It Measures | How to Calculate |
|--------|-----------------|------------------|
| **Volume** | How many people are talking about this | mention_count / max_mention_count_across_all_themes. The theme with the most mentions gets 1.0. |
| **Reach** | How many different customers are affected | unique_customers / max_unique_customers_across_all_themes. The most diverse theme gets 1.0. |
| **Urgency** | How urgent are the requests | Weighted score: (critical×4 + high×3 + medium×2 + low×1) / (total_mentions × 4). All critical = 1.0, all low = 0.25. |
| **Sentiment** | How negative is the feedback | negative_count / total_mentions. All negative = 1.0 (most urgent to fix). All positive = 0.0. |
| **Strategic Fit** | How well this aligns with PM's goals | LLM scores 0.0-1.0 based on theme name+description vs PM's stated goals and target segments. |

### Final Score

`priority_score = (volume × weight_volume) + (reach × weight_reach) + (urgency × weight_urgency) + (sentiment × weight_sentiment) + (strategic_fit × weight_strategic_fit)`

Default weights: volume=0.25, reach=0.20, urgency=0.25, sentiment=0.15, strategic_fit=0.15.

PM can adjust these in Settings.

### Score Breakdown

Every theme stores a score_breakdown JSONB that shows the per-factor scores:

```
{
  "volume": { "raw": 47, "normalized": 0.82, "weighted": 0.205 },
  "reach": { "raw": 12, "normalized": 0.70, "weighted": 0.14 },
  "urgency": { "raw": 3.2, "normalized": 0.80, "weighted": 0.20 },
  "sentiment": { "raw": 0.68, "normalized": 0.68, "weighted": 0.102 },
  "strategic_fit": { "raw": 0.85, "normalized": 0.85, "weighted": 0.1275 },
  "final_score": 0.7745,
  "weights_used": { "volume": 0.25, "reach": 0.20, "urgency": 0.25, "sentiment": 0.15, "strategic_fit": 0.15 }
}
```

This makes every score explainable. A PM can look at a theme and understand exactly why it's ranked where it is.

### Strategic Fit (LLM Call)

For each theme, send the theme name + description + the PM's goals and target segments to the LLM:

**Prompt:** "Given these product goals: [goals]. Target segments: [segments]. Rate how well this theme aligns: Theme: [name]. Description: [description]. Segment breakdown: [breakdown]. Return JSON: { score: 0.0-1.0, reasoning: 'one sentence explanation' }."

This is a batched call — send all themes in one LLM call if possible, or batch 5-10 at a time. Do not make one LLM call per theme if there are 20 themes.

If PM has no scoring config (no goals set), set strategic_fit to 0.5 for all themes (neutral).

### When Scoring Runs

- After clustering completes (automatic).
- When PM updates scoring config (weights, goals, target segments) — re-score all current themes without re-clustering.
- Manual trigger: PM clicks "Re-score" button.

---

## Services

### embedding_service.py

Functions:
- `generate_embedding(text)` — Single text to vector.
- `generate_embeddings_batch(texts)` — Batch encoding.
- `get_model()` — Return cached model singleton.

### clustering_service.py

Functions:
- `run_clustering(db, org_id)` — Full clustering flow: load embeddings, run HDBSCAN, create themes, name them, assign items, compute stats, run scoring. Return summary (clusters found, outliers, items processed).
- `compute_cluster_stats(db, items_in_cluster)` — Calculate mention_count, unique_customers, segment_breakdown, urgency_breakdown, sentiment_breakdown, top_quotes.
- `compute_centroid(embeddings)` — Average of all vectors.
- `should_recluster(db, org_id)` — Check if unclustered items exceed threshold.

### theme_service.py

Functions:
- `get_themes(db, org_id, page, page_size, sort_by)` — List current themes, sorted by priority_score (default), mention_count, or name. Paginated.
- `get_theme(db, org_id, theme_id)` — Single theme with full details.
- `get_theme_feedback(db, org_id, theme_id, page, page_size)` — Paginated feedback items belonging to this theme.
- `name_theme(items_in_cluster)` — Call LLM with top quotes, return name and description.
- `get_outliers(db, org_id, page, page_size)` — List feedback items that are outliers (not in any theme).

### scoring_service.py

Functions:
- `score_themes(db, org_id)` — Score all current themes for the org. Load scoring config, calculate each factor, compute final score, store breakdown.
- `calculate_volume_score(theme, max_mentions)` — Normalize mention count.
- `calculate_reach_score(theme, max_customers)` — Normalize unique customers.
- `calculate_urgency_score(theme)` — Weighted urgency formula.
- `calculate_sentiment_score(theme)` — Negative ratio.
- `calculate_strategic_fit(themes, goals, target_segments)` — LLM batch call for all themes.
- `get_scoring_config(db, org_id)` — Get or create default config.
- `update_scoring_config(db, org_id, data)` — Update weights/goals/segments. Validate weights sum to 1.0. Trigger re-scoring.

---

## Tasks (Celery)

### tasks/embedding_tasks.py

- `generate_embedding_task(feedback_item_id, org_id)` — Generate and store embedding for one item.

### tasks/clustering_tasks.py

- `run_clustering_task(org_id)` — Run full clustering + theme creation + scoring.

### Modify Existing Tasks

**tasks/enrichment_tasks.py** — After enrichment completes, if the item has a pain_point and no embedding, queue `generate_embedding_task`.

**After embedding is generated** — Check `should_recluster()`. If threshold is exceeded, queue `run_clustering_task`.

---

## Schemas (Pydantic)

### schemas/theme.py

- `ThemeResponse` — id, name, description, mention_count, unique_customers, segment_breakdown, urgency_breakdown, sentiment_breakdown, top_quotes, priority_score, score_breakdown, is_current, created_at.
- `ThemeListResponse` — Paginated list of themes.
- `ThemeDetailResponse` — Theme + paginated feedback items.

### schemas/scoring.py

- `ScoringConfigResponse` — goals, target_segments, all 5 weights.
- `ScoringConfigUpdateRequest` — All fields optional. Weights validated to sum to 1.0.
- `ScoreBreakdownResponse` — Per-factor scores with raw, normalized, and weighted values.

### schemas/clustering.py

- `ClusteringResultResponse` — clusters_found, outliers, items_processed, duration_ms.
- `ReclusterRequest` — Empty (just triggers it). Optional: min_cluster_size override.

---

## Models (SQLAlchemy)

### New Models

- `backend/app/models/theme.py` — Theme model.
- `backend/app/models/scoring_config.py` — ScoringConfig model.

### Updated Models

- `backend/app/models/feedback_item.py` — Add embedding (Vector), theme_id (FK), is_outlier, clustered_at.

---

## Alembic Migrations

**`007_add_embedding_to_feedback_items`** — Add embedding vector(384) column, theme_id FK, is_outlier, clustered_at. Create HNSW index on embedding column.

**`008_create_themes_and_scoring_configs`** — Create themes table and scoring_configs table with all columns and indexes.

---

## API Endpoints

### Themes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/v1/themes | Yes | List current themes, sorted by priority_score. Paginated. |
| GET | /api/v1/themes/{id} | Yes | Get theme detail with feedback items. |
| GET | /api/v1/themes/{id}/feedback | Yes | Paginated feedback items in this theme. |
| GET | /api/v1/themes/outliers | Yes | Feedback items not in any theme. |

### Clustering

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/v1/clustering/run | Yes | Trigger re-clustering. Returns immediately with job status. |
| GET | /api/v1/clustering/status | Yes | Check if clustering is running, last run time, items pending. |

### Scoring

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/v1/scoring/config | Yes | Get current scoring configuration. |
| PATCH | /api/v1/scoring/config | Yes | Update scoring config (weights, goals, segments). Triggers re-scoring. |
| POST | /api/v1/scoring/re-score | Yes | Manually trigger re-scoring without re-clustering. |

---

## Frontend Changes

### Theme Dashboard (NEW — this becomes the main page)

This is the most important page in the product. It replaces the dashboard as the primary view after a PM has feedback ingested and clustered.

**Layout:**
- **Header area:** "Your Priorities" title. Clustering status (last run, items pending). "Re-cluster" button if new items are pending.
- **Scoring controls:** Collapsible panel showing current weights as sliders (0-100 for each factor). PM drags sliders to adjust. "Apply" button recalculates scores.
- **Theme list (main content):** Ranked list of themes, ordered by priority_score (highest first).

**Each theme card shows:**
- Rank number (#1, #2, #3...)
- Theme name (bold, prominent)
- Priority score (large number, e.g., "8.2 / 10")
- Score bar showing the 5 factors as a stacked/segmented bar (visual breakdown)
- Mention count with icon (e.g., "47 mentions")
- Unique customers with icon (e.g., "12 customers")
- Segment pills: Enterprise (blue), Mid-Market (purple), SMB (gray) with counts
- Urgency bar: visual breakdown of critical/high/medium/low
- Top 2 verbatim quotes (truncated)
- Click to expand → goes to theme detail page

### Theme Detail Page (NEW)

Shows everything about a single theme:

- Theme name and description
- Full score breakdown: each factor with raw value, normalized value, weight used, and weighted contribution. Show this as a horizontal bar chart or table.
- "Why this score" explanation: "Volume: 47 mentions (82nd percentile). Reach: 12 unique customers. Urgency: 80% high or critical. Sentiment: 68% negative. Strategic fit: 85% aligned with your goal 'Improve enterprise retention'."
- Segment breakdown: visual chart (pie or bar)
- Urgency breakdown: visual chart
- Feedback items list: paginated, showing each item with content, author, source, urgency badge, customer name
- Top quotes highlighted

### Scoring Settings (in Settings page)

New section in Settings:

**Product Goals:**
- PM enters 1-5 goals as text (e.g., "Improve enterprise retention", "Reduce onboarding friction").
- These feed into the strategic_fit scoring.

**Target Segments:**
- Checkboxes: Enterprise, Mid-Market, SMB.
- Selected segments get extra weight in the strategic_fit calculation.

**Scoring Weights:**
- 5 sliders: Volume, Reach, Urgency, Sentiment, Strategic Fit.
- Each slider goes 0-100.
- Display shows the percentage.
- Constraint: they must sum to 100%. If PM adjusts one, others auto-adjust proportionally.
- "Reset to defaults" button.
- "Apply" saves and triggers re-scoring.

### Dashboard Updates

- The old dashboard becomes a summary/overview page.
- Add a "Top 5 Priorities" card showing the top 5 themes by score with their scores.
- Add "Clustering Status" card: last run, clusters found, outliers, items pending clustering.
- Link to the full Theme Dashboard.

### Feedback List Updates

- Add a "Theme" column showing the assigned theme name (or "Outlier" or "Unclustered").
- Filter by theme (dropdown of current theme names).
- Click the theme name → go to theme detail page.

### Sidebar Updates

- Add "Priorities" link → Theme Dashboard (this should be the most prominent link).
- Reorder sidebar: Priorities (top), Feedback, Customers, Settings.

---

## Testing

### test_embedding_service.py
1. Generate embedding returns a 384-dimensional vector.
2. Generate embeddings batch processes multiple texts.
3. Model is loaded once (singleton), not per call.
4. Empty text or None input returns None (does not crash).

### test_clustering_service.py
1. Cluster 20 items with 3 distinct topics — creates 3 clusters.
2. Items with unique/unrelated content become outliers.
3. Fewer than min_cluster_size items — no clusters, all outliers.
4. Centroid is correctly computed (average of embeddings).
5. Theme stats (mention_count, segment_breakdown, urgency_breakdown) are correct.
6. Top quotes are selected (closest to centroid).
7. Historical themes marked as is_current=false when re-clustering.
8. Clustering filters by org_id (multi-tenant isolation).

### test_theme_service.py
1. Get themes returns only current themes sorted by priority_score.
2. Get theme returns full details.
3. Get theme feedback returns paginated items for that theme.
4. Get outliers returns unclustered items.
5. Theme from another org is not accessible.

### test_scoring_service.py
1. Volume score: theme with most mentions gets 1.0, others proportional.
2. Reach score: theme with most unique customers gets 1.0.
3. Urgency score: all-critical theme gets 1.0, all-low theme gets 0.25.
4. Sentiment score: all-negative theme gets 1.0, all-positive gets 0.0.
5. Strategic fit: LLM returns scores (mock LLM call).
6. Final score is weighted sum of all factors.
7. Weights must sum to 1.0 — validation rejects otherwise.
8. Default config created when none exists.
9. Update config triggers re-scoring (verify scores change when weights change).
10. Score breakdown is stored and matches calculated values.

### test_clustering_routes.py
1. POST /clustering/run triggers clustering task (mock Celery).
2. GET /clustering/status returns correct status.
3. Clustering for another org is not triggered.

### test_theme_routes.py
1. GET /themes returns ranked themes for current org.
2. GET /themes/{id} returns theme detail.
3. GET /themes/{id}/feedback returns paginated items.
4. Theme from another org returns 404.

### test_scoring_routes.py
1. GET /scoring/config returns current config (or defaults).
2. PATCH /scoring/config updates weights and triggers re-scoring.
3. PATCH with weights not summing to 1.0 returns 422.
4. POST /scoring/re-score triggers re-scoring.

---

## Non-Negotiable Rules for This Phase

Everything from Phases 1-4 still applies, plus:

1. **Embedding model is loaded once.** Do not reload the model per request or per item. Cache as a singleton. This is critical for performance.
2. **Clustering runs on ALL items for the org, not just new ones.** Clusters can shift as new data arrives. Always re-cluster from scratch.
3. **Historical themes are preserved.** When re-clustering, mark old themes as is_current=false. Don't delete them. PMs might want to see how priorities changed over time.
4. **Every score is explainable.** The score_breakdown field must show raw values, normalized values, and weighted contributions for all 5 factors. No black boxes.
5. **Weights must sum to 1.0.** Validate on save. Reject if they don't.
6. **LLM calls are batched.** Theme naming: one call per cluster (not per item). Strategic fit: batch all themes in one or few calls (not one per theme).
7. **Outliers are not hidden.** Show them in the UI so the PM knows some feedback didn't fit any cluster.
8. **Clustering is async.** Always runs as a Celery task. The API returns immediately. Frontend polls for status.
9. **pgvector index must exist.** Create an HNSW index on the embedding column. Without it, similarity searches on large datasets will be unbearably slow.

---

## What NOT to Build

- Chat/conversational interface (Phase 6)
- Evidence briefs (Phase 7)
- Solution design (Phase 7)
- Spec generation (Phase 8)
- Theme merging or splitting (future enhancement, not in any current phase)
- Manual theme creation (future enhancement)
- Feedback item reassignment between themes (future enhancement)

---

## Acceptance Criteria

Phase 5 is complete when ALL of these are true:

- [ ] Feedback items get embeddings generated automatically after extraction
- [ ] Embeddings are stored in pgvector and HNSW index is created
- [ ] Embedding model loads once (not per request) — verify in logs
- [ ] PM can trigger clustering manually
- [ ] Clustering runs automatically when threshold is exceeded
- [ ] HDBSCAN produces meaningful clusters (related feedback grouped together)
- [ ] Each cluster becomes a theme with LLM-generated name and description
- [ ] Outliers are identified and accessible in the UI
- [ ] Theme stats are correct: mention_count, unique_customers, segment/urgency/sentiment breakdowns
- [ ] Top quotes are selected (most representative, closest to centroid)
- [ ] Historical themes preserved when re-clustering (is_current toggled)
- [ ] PM can configure scoring weights in Settings (sliders that sum to 100%)
- [ ] PM can set product goals and target segments
- [ ] Weights validation: reject if they don't sum to 1.0
- [ ] All themes get a priority score with score_breakdown
- [ ] Theme Dashboard shows ranked themes (highest priority first)
- [ ] Each theme card shows: name, score, mention count, customers, segments, urgency, top quotes
- [ ] Theme Detail page shows full score breakdown with explanation
- [ ] Changing weights triggers re-scoring and the ranked list updates
- [ ] Setting goals affects strategic_fit scores
- [ ] Feedback list shows theme assignment
- [ ] Feedback list filterable by theme
- [ ] Sidebar has "Priorities" as the top link
- [ ] Multi-tenant: themes are org-scoped (one org can't see another's themes)
- [ ] All Phase 5 tests pass
- [ ] All Phase 1-4 tests still pass

---

## How to Give This to Cursor

1. Save this file as `D:\LinkedIn\Week4\docs\PHASE_5_SPEC.md`
2. Open Cursor's chat and type:

> Read `docs/PHASE_5_SPEC.md`. This is the spec for Phase 5. The `.cursorrules` file still applies. Do NOT start building yet. Create a detailed implementation plan first: list every file you will create or modify, what each contains, the order of work, and dependencies. Present the full plan and wait for my approval.

3. Review the plan. Approve or push back.
4. Let Cursor build.
5. Run through acceptance criteria.

---

## After Phase 5

Once all acceptance criteria pass, come back for Phase 6: Conversational Layer. That phase will add:
- Chat interface in the right sidebar
- PM can ask questions about their data: "What are enterprise customers most frustrated about?"
- Chat uses RAG (retrieval augmented generation) — searches embeddings for relevant feedback, sends context to LLM
- Chat has tool functions to query themes, filter feedback, compare segments
- Conversation history stored per user
