# Phase 7: Evidence Briefs & Solution Design — Verification Checklist

> Run through this checklist yourself AFTER Cursor says Phase 7 is complete.
> Every item must pass before moving to Phase 8.

---

## Docker & Infrastructure

- [ ] `docker-compose up --build` starts all services without errors
- [ ] All Phase 1-6 tests still pass
- [ ] Run: `docker-compose exec backend pytest app/tests/ -v`

---

## Brief Generation — Trigger

- [ ] Go to the Theme Dashboard → click "Generate Brief" on the #1 priority theme
- [ ] API returns immediately with a brief_id and status "generating"
- [ ] You're taken to the Brief page (or a loading state appears)

---

## Brief Generation — Progress

- [ ] A progress indicator shows which section is being generated (e.g., "Generating section 2 of 7: Customer Impact...")
- [ ] Sections appear one by one as they complete (not all at once at the end)
- [ ] You can start reading Section 1 while Section 3 is still generating
- [ ] Poll the status endpoint — it correctly reports sections_completed and current_section
- [ ] When all 7 sections are done, status changes to "completed"

---

## Section Quality — Problem Statement

- [ ] 2-3 paragraphs describing the problem
- [ ] Cites actual quotes from your feedback data (not made up)
- [ ] Written for stakeholders (not too technical, not too vague)

---

## Section Quality — Customer Impact

- [ ] Shows segment breakdown (enterprise: X, mid-market: Y, SMB: Z)
- [ ] Names specific customers (real customers from your data)
- [ ] Shows urgency distribution
- [ ] Gives a sense of scope ("affects X% of enterprise customers")

---

## Section Quality — Evidence Summary

- [ ] Presents actual verbatim quotes from feedback
- [ ] Quotes are organized (by urgency, sub-theme, or another logical grouping)
- [ ] Not just a raw list — synthesized into a narrative with context

---

## Section Quality — Trend Analysis

- [ ] References actual dates/timeframes from feedback timestamps
- [ ] Notes if mentions are increasing or decreasing
- [ ] If insufficient historical data, honestly says so (not fabricated trends)

---

## Section Quality — Business Case

- [ ] References the priority score and its factors (volume, reach, urgency, etc.)
- [ ] References PM's stated product goals (from scoring config)
- [ ] Connects the theme to business outcomes (retention, expansion, etc.)

---

## Section Quality — Recommended Action

- [ ] Specific and actionable (not "consider improving authentication")
- [ ] References actual feature gaps from the feedback
- [ ] Suggests scope (what to include now vs defer)

---

## Section Quality — Risks & Considerations

- [ ] Mentions real risks (not generic filler)
- [ ] Considers resource tradeoffs with other themes
- [ ] Notes any conflicting feedback or ambiguity within the theme

---

## Section Regeneration

- [ ] Click "Regenerate" on the Problem Statement section
- [ ] Old content is saved to edit_history
- [ ] New content replaces it (may differ slightly from original)
- [ ] generated_at is updated
- [ ] Other sections are NOT affected

---

## Section Editing

- [ ] Click "Edit" on any section → switches to an editable text area
- [ ] Make changes and save
- [ ] Section shows "Edited" badge
- [ ] Old content saved to edit_history
- [ ] Revert option restores the previous version
- [ ] Regenerating OTHER sections does NOT overwrite your edited section

---

## Versioning

- [ ] Note the current brief's version number (should be 1)
- [ ] Go back to the theme and click "Generate Brief" again
- [ ] A new brief is created with version 2
- [ ] Previous brief (version 1) is still accessible via the version selector
- [ ] Only version 2 has is_current=true

---

## Solution Evaluator

- [ ] Open a completed brief → find the "Evaluate Solution" panel
- [ ] Type a solution description that addresses SOME of the theme's pain points
- [ ] Click "Evaluate"
- [ ] See results:
  - [ ] Coverage score as a percentage
  - [ ] Green checks for addressed pain points
  - [ ] Red X for unaddressed pain points
  - [ ] Strengths list
  - [ ] Gaps list
  - [ ] Recommended additions
- [ ] Coverage score is reasonable (not always 100% or always 0%)

### Solution Evaluator — Accuracy

- [ ] Describe a solution that addresses ALL pain points → high coverage (>80%)
- [ ] Describe a solution that addresses NONE → low coverage (<30%)
- [ ] Describe a partial solution → proportional coverage
- [ ] Gaps listed are actually things the solution doesn't cover

### Solution Evaluator — Re-evaluation

- [ ] Edit the solution description and click "Evaluate" again
- [ ] New evaluation replaces the old one
- [ ] Results change based on the updated solution

---

## Export

- [ ] Click "Export as Markdown"
- [ ] A clean .md file is downloadable (or content is copyable)
- [ ] Markdown is well-formatted: proper headers, quotes, no JSON artifacts
- [ ] All 7 sections are included in order
- [ ] Solution evaluation is included (if one exists)

---

## Theme Dashboard Integration

- [ ] Theme cards show a brief status: nothing (no brief yet), "Brief Ready" badge, or "Generating..."
- [ ] "Generate Brief" button on theme cards
- [ ] "View Brief" button appears once a brief exists
- [ ] Clicking "View Brief" navigates to the Brief page

---

## Theme Detail Integration

- [ ] Theme Detail page has a "Brief" tab or section
- [ ] If no brief exists: shows "Generate Evidence Brief" button
- [ ] If brief exists: shows the brief inline or links to the Brief page

---

## Chat Integration

- [ ] Open chat → ask "Generate a brief for [theme name]"
- [ ] The chat triggers brief generation and provides a link or confirmation
- [ ] Ask "What does the brief say about the business case for [theme]?"
- [ ] The chat responds with content from the brief

---

## Multi-Tenant Isolation

- [ ] Briefs are scoped to org_id
- [ ] A second org cannot see the first org's briefs
- [ ] Brief for a theme from another org returns 404

---

## Error Handling

- [ ] If LLM fails during one section, that section shows a retry option
- [ ] Other sections still generate successfully
- [ ] If LLM is completely down, brief status is set to "failed"
- [ ] Failed briefs can be retried (generate again)

---

## Quick API Spot Checks

Open `http://localhost:8000/docs` and test:

- [ ] `POST /api/v1/briefs/generate` — returns brief_id and status
- [ ] `GET /api/v1/briefs/{id}` — returns brief with sections
- [ ] `GET /api/v1/briefs/{id}/status` — returns generation progress
- [ ] `GET /api/v1/briefs/theme/{theme_id}` — returns all versions
- [ ] `GET /api/v1/briefs/theme/{theme_id}/current` — returns latest
- [ ] `PATCH /api/v1/briefs/{id}/sections/{key}` — edits section
- [ ] `POST /api/v1/briefs/{id}/sections/{key}/regenerate` — regenerates section
- [ ] `POST /api/v1/briefs/{id}/evaluate-solution` — returns evaluation
- [ ] `GET /api/v1/briefs/{id}/export/markdown` — returns clean markdown
- [ ] All error responses follow: `{ "error": { "code": "...", "message": "..." } }`

---

## Tests

- [ ] All Phase 7 backend tests pass
- [ ] All Phase 6 backend tests still pass
- [ ] All Phase 5 backend tests still pass
- [ ] All Phase 4 backend tests still pass
- [ ] All Phase 3 backend tests still pass
- [ ] All Phase 2 backend tests still pass
- [ ] All Phase 1 backend tests still pass
- [ ] Run: `docker-compose exec backend pytest app/tests/ -v`

---

## The "Would I Share This?" Test

The most important test. Read the completed brief and ask yourself:

1. **Would I send this to my VP of Product?** If the brief reads like something a competent analyst wrote — specific, evidence-backed, well-structured — it passes.

2. **Does the evidence feel real?** Every quote should be traceable to actual feedback. No generic filler like "customers want a better experience."

3. **Is the recommended action useful?** If you read it and think "yes, that's actually what I'd propose" — it passes. If it's generic ("consider improving this area") — it fails.

4. **Does the solution evaluator catch real gaps?** Describe a deliberately incomplete solution. Does it identify what's missing? If it rubber-stamps everything, it fails.

5. **Would this save me time?** A PM manually writing this brief would take 2-4 hours. If the generated version gets them 80% there in 30 seconds, Phase 7 is a success.

---

## If Something Fails

Tell Cursor: "Phase 7 checklist item [X] failed. Here's what happened: [describe]. Fix it following the spec in docs/PHASE_7_SPEC.md."

Once everything passes, move to Phase 8 — the final phase.
