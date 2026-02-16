# Phase 5 — Prioritization (plan and architecture)

Plain-English description of how we score and prioritize themes.

---

## Plan

**Goal:** Let the product manager define what “important” means and see which themes matter most.

We wanted:

- The PM to create **priorities** (e.g. “Enterprise segment,” “High urgency,” “Strategic themes”).
- Priorities to be **attached to themes** (or used as global goals).
- The system to **score** each theme using: volume of feedback, urgency, sentiment, how well it fits the PM’s segments and strategy.
- The PM to **tune weights** (e.g. “care more about urgency than volume”) so the score reflects their strategy.
- Dashboards and theme lists to show **priority score** so the PM can decide what to brief next.

---

## Architecture (how it works)

**Data model:**

- **Priorities:** Name, optional description, optional weights or criteria. Stored per organization.
- **Theme–priority link:** We know which priorities apply to which themes (or we score all themes against global priorities).
- **PM settings:** Optional table or fields for scoring weights (e.g. weight for volume, urgency, sentiment, segment fit). Defaults if not set.

**Scoring:**

- We compute a **priority score** per theme. Inputs typically include: number of feedback items in the theme, average or max urgency, sentiment mix, whether feedback is from target segments (e.g. enterprise). We use **SQL** to aggregate (counts, averages) and optionally the **LLM** for “strategic fit” or naming. The formula uses the PM’s weights when present.
- Scoring can run when clustering completes, or when the PM changes weights, or on demand. Results are stored on the **themes** table (e.g. priority_score) so the UI can sort and filter by “most important first.”

**UI:**

- The PM sees priorities in a list, can create/edit them, and can attach them to themes. The theme list and dashboard show the computed score so the PM can choose the next theme to brief.
