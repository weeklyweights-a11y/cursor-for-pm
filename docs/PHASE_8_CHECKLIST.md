# Phase 8: Agent-Ready Specs — Verification Checklist

> Run through this checklist yourself AFTER Cursor says Phase 8 is complete.
> This is the final phase. Every item must pass.

---

## Docker & Infrastructure

- [ ] `docker-compose up --build` starts all services without errors
- [ ] All Phase 1-7 tests still pass
- [ ] Run: `docker-compose exec backend pytest app/tests/ -v`

---

## Spec Generation — Prerequisites

- [ ] Go to a theme that has a completed evidence brief WITH a solution evaluation
- [ ] "Generate Spec" button is visible and enabled
- [ ] Go to a theme that has a brief WITHOUT a solution evaluation
- [ ] "Generate Spec" button is disabled or shows "Evaluate a solution first" message

---

## Spec Configuration Modal

- [ ] Click "Generate Spec" → configuration modal appears
- [ ] Scope selector shows "MVP" and "Full" options
- [ ] Audience selector shows "AI Agent," "Engineer," and "Mixed" options
- [ ] Custom instructions text area is available (optional)
- [ ] "Generate" button starts the generation

---

## Spec Generation — Progress

- [ ] After clicking Generate, a spec record is created and you see a progress view
- [ ] Sections appear one by one as they complete (not all at once)
- [ ] Progress indicator shows current section (e.g., "Generating section 4 of 8: Functional Requirements")
- [ ] You can read early sections while later ones are still generating
- [ ] When all 8 sections are done, status changes to "completed"

---

## Section Quality — Executive Summary

- [ ] 3-5 sentences
- [ ] States the problem, the solution, and the expected impact
- [ ] No jargon — readable by anyone

---

## Section Quality — Background & Evidence

- [ ] Cites real customer quotes from your data
- [ ] Includes customer names and segments (if available)
- [ ] Connects evidence to the solution being spec'd

---

## Section Quality — User Stories

- [ ] Standard format: "As a [persona], I want to [action] so that [outcome]"
- [ ] Each story has acceptance criteria (Given/When/Then or checkbox format)
- [ ] Each story has a priority label (Must-have / Should-have / Nice-to-have)
- [ ] **Evidence trail:** Each story references specific pain points or customer quotes
- [ ] Stories make sense — they describe real user needs, not abstract concepts

---

## Section Quality — Functional Requirements

- [ ] Numbered requirements (FR-1, FR-2, etc.)
- [ ] Each requirement references which user story it supports (US-1, US-3, etc.)
- [ ] Requirements are specific and testable (not vague)

---

## Section Quality — Technical Guidance

- [ ] Content matches the target audience you selected:

### If you selected "AI Agent":
- [ ] Highly structured with explicit instructions
- [ ] Specific file paths, function names, or approach suggestions
- [ ] Reads like our phase specs (prescriptive, detailed)

### If you selected "Engineer":
- [ ] Architecture-level guidance
- [ ] Key decisions highlighted
- [ ] Room for interpretation — doesn't micromanage

### If you selected "Mixed":
- [ ] Structured enough to act on
- [ ] Readable enough for a human

---

## Section Quality — Data Model Changes

- [ ] Suggests specific tables or columns to create/modify
- [ ] For AI Agent audience: column names, types, constraints
- [ ] For Engineer audience: conceptual model, key relationships

---

## Section Quality — API Contracts

- [ ] Lists specific endpoints (method, path, auth)
- [ ] Includes request/response shapes
- [ ] For AI Agent audience: full schemas with types
- [ ] For Engineer audience: key endpoints described, implementation flexible

---

## Section Quality — Testing & Verification

- [ ] Verification checklist tied to acceptance criteria
- [ ] Specific test descriptions (not just "test it works")
- [ ] Edge cases mentioned
- [ ] Definition of done is clear

---

## Scope Differences — MVP vs Full

Generate two specs for the same theme — one MVP, one Full:

- [ ] MVP spec has fewer user stories (only must-have)
- [ ] Full spec has more user stories with priority labels
- [ ] MVP technical guidance is more focused/minimal
- [ ] Full spec covers edge cases and optional features
- [ ] The difference is noticeable — not just cosmetic

---

## Audience Differences — AI Agent vs Engineer

Generate two specs for the same theme — one AI Agent, one Engineer:

- [ ] AI Agent spec is more prescriptive (specific columns, endpoints, file paths)
- [ ] Engineer spec is more advisory (architecture guidance, key decisions)
- [ ] The difference is noticeable — not just formatting

---

## Evidence Trail

This is the most important feature of Phase 8:

- [ ] User stories reference specific customer quotes or pain points
- [ ] You can trace any requirement back to actual customer feedback
- [ ] No requirement exists without evidence
- [ ] The evidence trail would convince a skeptical stakeholder that this feature is justified

---

## Section Regeneration

- [ ] Click "Regenerate" on any section → new content replaces old
- [ ] Old content saved to edit history
- [ ] Other sections are NOT affected

---

## Section Editing

- [ ] Click "Edit" on any section → editable text area
- [ ] Make changes, save → section shows "Edited" badge
- [ ] Regenerating OTHER sections does not overwrite edited sections
- [ ] Revert option restores previous version

---

## Versioning

- [ ] Note the current spec version number (should be 1)
- [ ] Generate a new spec for the same brief
- [ ] New spec has version 2
- [ ] Previous spec (version 1) is still accessible
- [ ] Only version 2 has is_current=true

---

## Export — Standard Markdown

- [ ] Click "Export Markdown"
- [ ] Clean, well-formatted markdown file
- [ ] All 8 sections present in order
- [ ] No JSON artifacts or debug metadata
- [ ] Could paste into Notion/Confluence and it looks professional

---

## Export — Cursor Format

- [ ] Click "Export for Cursor"
- [ ] Output matches our phase spec format:
  - [ ] Goal and Done-means at the top
  - [ ] Evidence summary
  - [ ] Database tables as markdown tables
  - [ ] API endpoints as markdown tables
  - [ ] Acceptance criteria as checkboxes
  - [ ] Non-negotiable rules
  - [ ] Evidence trail
- [ ] You could paste this into Cursor and say "Build this"
- [ ] An AI agent reading this would have everything it needs

---

## Custom Instructions

- [ ] Generate a spec with custom instructions like "We use PostgreSQL, FastAPI, React with Tailwind"
- [ ] Technical guidance and data model sections reference these technologies
- [ ] Generate without custom instructions
- [ ] Technical sections are more generic (no specific stack assumptions)

---

## Brief Page Integration

- [ ] Brief page shows "Generate Spec" button at the bottom
- [ ] Button disabled if no solution evaluation exists
- [ ] After spec exists: "View Spec" button appears
- [ ] Theme Dashboard shows "Spec Ready" badge on themes with specs

---

## Chat Integration

- [ ] Open chat → "Generate a spec for [theme name]" → triggers spec generation (if brief + eval exist)
- [ ] "Show me the user stories for [theme name]" → returns user stories from the spec
- [ ] "What endpoints does the [theme] spec define?" → returns API contract info

---

## Multi-Tenant Isolation

- [ ] Specs are scoped to org_id
- [ ] Another org cannot see your specs
- [ ] Spec for a theme from another org returns 404

---

## Error Handling

- [ ] If LLM fails during a section, that section shows retry option
- [ ] Other sections still generate
- [ ] If brief has no solution evaluation, spec generation is blocked with clear message
- [ ] Generating for a nonexistent brief returns 404

---

## Quick API Spot Checks

Open `http://localhost:8000/docs` and test:

- [ ] `POST /api/v1/specs/generate` — returns spec_id and status
- [ ] `GET /api/v1/specs/{id}` — returns spec with sections
- [ ] `GET /api/v1/specs/{id}/status` — returns progress
- [ ] `GET /api/v1/specs/brief/{brief_id}` — returns versions
- [ ] `GET /api/v1/specs/brief/{brief_id}/current` — returns latest
- [ ] `GET /api/v1/specs/theme/{theme_id}` — returns all specs for theme
- [ ] `PATCH /api/v1/specs/{id}/sections/{key}` — edits section
- [ ] `POST /api/v1/specs/{id}/sections/{key}/regenerate` — regenerates section
- [ ] `GET /api/v1/specs/{id}/export/markdown` — clean markdown
- [ ] `GET /api/v1/specs/{id}/export/cursor` — Cursor-optimized format
- [ ] All error responses follow: `{ "error": { "code": "...", "message": "..." } }`

---

## Tests

- [ ] All Phase 8 backend tests pass
- [ ] All Phase 7 backend tests still pass
- [ ] All Phase 6 backend tests still pass
- [ ] All Phase 5 backend tests still pass
- [ ] All Phase 4 backend tests still pass
- [ ] All Phase 3 backend tests still pass
- [ ] All Phase 2 backend tests still pass
- [ ] All Phase 1 backend tests still pass
- [ ] Run: `docker-compose exec backend pytest app/tests/ -v`

---

## THE FULL LOOP TEST

This is the final boss. Run through the entire pipeline end-to-end:

### Step 1: Ingest
- [ ] Upload a CSV with 50+ feedback items
- [ ] Verify items appear in the feedback list

### Step 2: Extract
- [ ] All items get pain points, topics, urgency, sentiment extracted
- [ ] Extraction stats on dashboard show all completed

### Step 3: Enrich
- [ ] Upload a customer CSV
- [ ] Feedback items get matched to customers
- [ ] Exact matches happen, fuzzy matches go to review queue

### Step 4: Cluster & Prioritize
- [ ] Trigger clustering → themes appear on the Theme Dashboard
- [ ] Each theme has a priority score with explainable breakdown
- [ ] Themes are ranked by priority

### Step 5: Chat
- [ ] Ask the chat "What should I focus on?" → mentions top themes
- [ ] Ask about a specific theme → gives evidence-backed analysis

### Step 6: Evidence Brief
- [ ] Generate a brief for the top theme
- [ ] All 7 sections are meaningful and grounded in data
- [ ] Problem statement cites real quotes

### Step 7: Solution Evaluation
- [ ] Describe a solution in the brief's evaluator
- [ ] Get coverage score, addressed/missed pain points

### Step 8: Agent-Ready Spec
- [ ] Generate a spec from the brief (MVP scope, AI Agent audience)
- [ ] All 8 sections are meaningful
- [ ] User stories have acceptance criteria AND evidence trails
- [ ] Export the Cursor-optimized format
- [ ] Read it. Could you hand this to Cursor and say "Build this"?

### The Verdict
- [ ] **The exported spec traces every requirement back to a real customer quote**
- [ ] **A PM who started with a messy CSV of feedback now has an actionable spec in under 30 minutes**
- [ ] **The loop is closed: Feedback → Signals → Themes → Priorities → Evidence → Solution → Spec → Code**

---

## The "Would an Engineer Thank Me?" Test

Read the Cursor-optimized export and ask:

1. **Does it explain WHY this feature matters?** Not "customers want SSO" but "12 enterprise customers are blocked on deployment because they can't enforce security policies — here's what they said."

2. **Are the user stories clear enough to estimate?** An engineer should read a story and think "I know what to build and how to verify it's done."

3. **Is the technical guidance actionable?** For AI Agent audience: specific enough that Cursor could start building. For Engineer audience: clear enough that a dev can make informed architecture decisions.

4. **Could this replace a 2-hour planning meeting?** If the spec contains everything the team would discuss in that meeting — the problem, the evidence, the requirements, the acceptance criteria — then Phase 8 is a success.

5. **Is the evidence trail convincing?** If a VP asks "why are we building this?" the PM can point to the spec and say "because these 47 customers told us to — here are their words."

---

## If Something Fails

Tell Cursor: "Phase 8 checklist item [X] failed. Here's what happened: [describe]. Fix it following the spec in docs/PHASE_8_SPEC.md."

---

## Congratulations

If everything passes — all 8 phases, all tests, the full loop test — the product is feature-complete.

**Next steps:**
1. Record a 60-second demo video of the full loop
2. Write up the project as a case study for your portfolio
3. Push to GitHub with a clean README
4. Post on LinkedIn: "I built an 8-layer AI product in [X] weeks"
5. Deploy to production and invite beta PMs
6. Come back and we'll plan the go-to-market
