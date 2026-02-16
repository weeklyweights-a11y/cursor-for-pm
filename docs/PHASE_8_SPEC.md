# Phase 8: Agent-Ready Specs

> **Goal:** PMs can generate implementation specs directly from evidence briefs — structured documents designed to be consumed by AI coding agents (Cursor, Claude Code). Each spec includes: user stories with acceptance criteria, technical requirements, data model changes, API contracts, and the evidence trail linking every requirement back to customer feedback. The full loop closes: Feedback → Signals → Themes → Priorities → Evidence Brief → Solution → Spec → Code.
>
> **Done means:** A PM clicks "Generate Spec" on an evidence brief that has a solution evaluation. Within 60 seconds, they have a structured implementation spec with user stories, acceptance criteria, technical guidance, and a linked evidence trail. They can hand this directly to Cursor or Claude Code (or a human engineer) and say "build this." Every requirement traces back to a real customer quote.

---

## Context for the AI Agent

This is Phase 8 of 8. The final phase. Phases 1-7 are complete — you have the entire pipeline: authentication, feedback ingestion, LLM extraction, customer enrichment, embeddings, clustering, prioritization, conversational chat, evidence briefs, and solution evaluation.

This phase produces the last artifact: the spec that turns a PM's decision into engineering action. It's the bridge between "we decided to build SSO" and "here's exactly what to build, why, and how to verify it's done."

Read `.cursorrules` before starting. All rules apply.

**Project root:** `D:\LinkedIn\Week4`

---

## What You Are Building

Two things:

1. **Spec Generator** — Takes an evidence brief (with its solution evaluation) and generates a structured implementation spec. The spec has multiple sections designed for different audiences: a summary for stakeholders, user stories for PMs/designers, technical requirements for engineers, and an evidence trail for accountability.

2. **Spec Customization** — PM can adjust the spec's scope (MVP vs full), target audience (engineer vs AI agent vs mixed), and technical depth before generating. PM can also edit and regenerate individual sections.

---

## New Dependencies

No new Python packages needed. Uses existing LLM service and all previous data layers.

---

## Database Changes

### New Table: specs

Stores generated implementation specs. Linked to a brief (which is linked to a theme).

| Column | Type | Rules |
|--------|------|-------|
| id | UUID (PK) | Auto-generated |
| org_id | UUID (FK to organizations) | Required, indexed |
| brief_id | UUID (FK to briefs) | Required, indexed |
| theme_id | UUID (FK to themes) | Required, indexed |
| created_by | UUID (FK to users) | Required |
| version | integer | Required. Auto-incremented per brief. |
| status | string (enum: generating, completed, failed) | Default "generating". |
| title | string, max 500 | Required. Generated from theme + solution. |
| scope | string (enum: mvp, full) | Required. PM's choice before generation. |
| target_audience | string (enum: ai_agent, engineer, mixed) | Required. Affects language and detail level. |
| sections | JSONB | Required. The spec content as structured sections (same shape as briefs). |
| config | JSONB | Nullable. Generation settings the PM chose (scope, audience, any custom instructions). |
| metadata | JSONB | Nullable. Generation metadata: models used, tokens consumed, duration_ms. |
| is_current | boolean | Default true. |
| created_at | timestamptz | Auto-generated |
| updated_at | timestamptz | Auto-generated |

**Indexes:** (org_id, brief_id) composite, (org_id, theme_id) composite, (org_id, is_current) composite.

---

## Spec Sections

Every spec has these 8 sections, generated in order:

### 1. Executive Summary
**What it answers:** "What are we building and why?"

**LLM context:** Theme name, brief's problem statement and business case, solution description and evaluation, coverage score.

**Output:** 3-5 sentence summary. Problem → solution → expected impact. Written for anyone — exec, PM, engineer, or AI agent. No jargon.

### 2. Background & Evidence
**What it answers:** "What customer evidence supports this?"

**LLM context:** Brief's evidence summary, customer impact section, top 10 verbatim quotes, priority score breakdown.

**Output:** Condensed evidence trail. Key quotes with attribution (customer name/segment if available). Links the "why" to the "what." This section exists so an engineer (or AI agent) understands the motivation without reading the full brief.

### 3. User Stories
**What it answers:** "What does the user need to be able to do?"

**LLM context:** Solution description, pain points addressed (from solution evaluation), feature gaps, product context (existing features, target users), scope setting (MVP vs full).

**Output:** Numbered user stories in standard format:
```
US-1: As a [persona], I want to [action] so that [outcome].
Acceptance Criteria:
- [ ] Given [context], when [action], then [expected result]
- [ ] Given [context], when [action], then [expected result]
Priority: Must-have / Should-have / Nice-to-have
Evidence: Links to pain points from [X] customers
```

For MVP scope: only must-have stories. For full scope: all stories with priority labels.

### 4. Functional Requirements
**What it answers:** "What must the system do?"

**LLM context:** User stories (from section 3), product context, existing features, solution description.

**Output:** Numbered list of functional requirements. Each references one or more user stories (e.g., "Supports US-1, US-3").

### 5. Technical Guidance
**What it answers:** "How should this be built?"

**LLM context:** Product context (existing stack if mentioned), functional requirements, scope, target_audience setting.

**Output varies by target_audience:**

**For ai_agent:** Highly structured, explicit instructions. Database table changes with column definitions. API endpoint contracts with request/response shapes. File paths to create or modify. Testing requirements. Similar to how our phase specs are written.

**For engineer:** Architecture suggestions, key decisions to make, integration points, libraries to consider. Less prescriptive, more advisory.

**For mixed:** A blend — structured enough for an AI agent to act on, readable enough for an engineer to review and override.

### 6. Data Model Changes
**What it answers:** "What database changes are needed?"

**LLM context:** Functional requirements, existing data model context (from product context or inferred), target_audience.

**Output:** Suggested table changes, new tables, new columns, indexes, relationships.

For ai_agent: includes specific column names, types, constraints, and migration instructions.
For engineer: higher-level description with key decisions highlighted.

### 7. API Contracts
**What it answers:** "What API endpoints are needed?"

**LLM context:** Functional requirements, user stories, data model changes, target_audience.

**Output:** Endpoint specifications with method, path, auth, request/response shapes, and notes.

For ai_agent: full request/response schemas with types.
For engineer: key endpoints with descriptions, details left to implementation.

### 8. Testing & Verification
**What it answers:** "How do we know it's done?"

**LLM context:** User stories with acceptance criteria, functional requirements, the brief's solution evaluation.

**Output:** A verification checklist: integration tests, manual verification steps, edge cases, and "definition of done" tied to acceptance criteria.

For ai_agent: specific test descriptions like our phase checklists.
For engineer: higher-level testing strategy.

---

## Generation Flow

### Pre-Generation Configuration

Before generating, the PM sees a configuration panel:

**Scope:**
- **MVP** — Only must-have user stories, minimal technical guidance, fastest to ship.
- **Full** — All user stories with priority labels, detailed technical guidance, comprehensive spec.

**Target Audience:**
- **AI Agent** — Structured for Cursor/Claude Code. Explicit, prescriptive, detailed schemas and contracts.
- **Engineer** — Readable for human developers. Architecture guidance, key decisions, room for interpretation.
- **Mixed** — Balanced. Structured enough for AI, readable for humans.

**Custom Instructions (optional):**
- Free text field where PM can add context: "We use PostgreSQL and FastAPI. Our frontend is React with Tailwind. We already have an auth system using JWT."
- This context is injected into technical sections.

### Generation Steps

1. PM clicks "Generate Spec" on a brief page (brief must be completed and must have a solution evaluation).
2. PM configures scope, audience, and optional custom instructions.
3. API creates a spec record with status="generating".
4. Celery task generates each section sequentially (same pattern as briefs):
   a. Load brief data (all sections, solution evaluation).
   b. Load theme data (feedback items, customers, scores).
   c. Load product context.
   d. For each section (1-8): build focused prompt, call LLM, validate, store, update record.
5. When all sections complete, set status="completed".
6. Failed sections get one retry, then marked as failed (partial spec is still usable).

---

## Evidence Trail

Every requirement, user story, and technical decision links back to customer evidence.

When generating user stories and requirements, the LLM prompt includes the pain points and feature gaps from feedback, each with an identifier. The LLM is instructed to reference these:

```
US-3: As an IT admin, I want to enforce SSO-only login so that I can comply with our security policy.
Acceptance Criteria:
- [ ] Admin can toggle "SSO required" in settings
- [ ] Non-SSO login is blocked when SSO is required
- [ ] Error message explains why direct login is disabled
Priority: Must-have
Evidence:
- "Our IT security policy requires SSO for all SaaS tools" — Acme Corp (Enterprise)
- "We can't deploy until we can enforce SSO-only access" — BigBank (Enterprise)
- Pain point addressed: IT teams cannot enforce security policies (8 mentions, 6 enterprise)
```

---

## Services

### spec_service.py

Functions:
- `generate_spec(db, org_id, brief_id, user_id, scope, target_audience, custom_instructions)` — Create spec record, validate brief has solution evaluation, queue generation task. Return spec_id.
- `get_spec(db, org_id, spec_id)` — Get a single spec with all sections.
- `get_specs_for_brief(db, org_id, brief_id)` — List all spec versions for a brief.
- `get_current_spec(db, org_id, brief_id)` — Get the latest spec for a brief.
- `get_specs_for_theme(db, org_id, theme_id)` — List all specs for a theme.
- `regenerate_section(db, org_id, spec_id, section_key)` — Regenerate one section.
- `edit_section(db, org_id, spec_id, section_key, new_content)` — Manual edit with history.
- `export_spec_markdown(db, org_id, spec_id)` — Generate complete markdown export.
- `export_spec_cursor_format(db, org_id, spec_id)` — Generate markdown optimized for Cursor's context window.
- `get_spec_generation_status(db, org_id, spec_id)` — Return progress.

### spec_generation_service.py

Functions:
- `generate_all_sections(db, org_id, spec_id, brief_id, config)` — Orchestrate sequential generation.
- `generate_executive_summary(brief_data, solution_eval, config)` — Build prompt, call LLM.
- `generate_background_evidence(brief_data, theme_data, config)` — Build prompt, call LLM.
- `generate_user_stories(solution_eval, pain_points, feature_gaps, product_context, config)` — Build prompt, call LLM.
- `generate_functional_requirements(user_stories, product_context, config)` — Build prompt, call LLM. Uses output from previous section.
- `generate_technical_guidance(requirements, product_context, config)` — Build prompt, call LLM.
- `generate_data_model(requirements, product_context, config)` — Build prompt, call LLM.
- `generate_api_contracts(requirements, user_stories, data_model, config)` — Build prompt, call LLM.
- `generate_testing(user_stories, requirements, solution_eval, config)` — Build prompt, call LLM.
- `load_generation_context(db, org_id, brief_id)` — Load brief + theme + feedback + customers + scores + product context.

---

## Prompt Templates

### backend/app/prompts/spec_sections.py

One prompt template per section. Each template has variations for scope (mvp/full) and target_audience (ai_agent/engineer/mixed).

### backend/app/prompts/spec_export.py

Template for the Cursor-optimized export format — converts spec sections into a single markdown document structured like our phase specs.

---

## Tasks (Celery)

### tasks/spec_tasks.py

- `generate_spec_task(spec_id, org_id, brief_id, config)` — Call spec_generation_service.generate_all_sections. Update status on completion or failure.

---

## Schemas (Pydantic)

### schemas/spec.py

- `GenerateSpecRequest` — brief_id (required UUID), scope (enum: mvp, full), target_audience (enum: ai_agent, engineer, mixed), custom_instructions (optional string).
- `SpecResponse` — id, brief_id, theme_id, version, status, title, scope, target_audience, sections (list), config, metadata, is_current, created_at, updated_at.
- `SpecListResponse` — Paginated list.
- `SpecSectionResponse` — key, title, content, generated_at, edited.
- `EditSpecSectionRequest` — section_key (string), content (string).
- `RegenerateSpecSectionRequest` — section_key (string).
- `SpecExportResponse` — markdown_content (string), filename (string), format (string: "standard" or "cursor").
- `SpecStatusResponse` — spec_id, status, sections_completed, sections_total, current_section.

---

## Models (SQLAlchemy)

### New Model

- `backend/app/models/spec.py` — Spec model with all columns.

Update models `__init__.py` to export.

---

## Alembic Migrations

**`011_create_specs`** — Create specs table with all columns and indexes.

---

## API Endpoints

### Specs

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/v1/specs/generate | Yes | Start spec generation. PM configures scope and audience. |
| GET | /api/v1/specs/{id} | Yes | Get spec with all sections. |
| GET | /api/v1/specs/{id}/status | Yes | Check generation progress. |
| GET | /api/v1/specs/brief/{brief_id} | Yes | List all spec versions for a brief. |
| GET | /api/v1/specs/brief/{brief_id}/current | Yes | Get the latest spec for a brief. |
| GET | /api/v1/specs/theme/{theme_id} | Yes | List all specs for a theme. |
| PATCH | /api/v1/specs/{id}/sections/{section_key} | Yes | Edit a section's content. |
| POST | /api/v1/specs/{id}/sections/{section_key}/regenerate | Yes | Regenerate a single section. |
| GET | /api/v1/specs/{id}/export/markdown | Yes | Export as standard markdown. |
| GET | /api/v1/specs/{id}/export/cursor | Yes | Export as Cursor-optimized markdown. |

---

## Frontend Changes

### Brief Page Updates

- "Generate Spec" button at the bottom of the brief page.
- Only enabled if brief is completed AND has a solution evaluation.
- If no solution evaluation: "Evaluate a solution first to generate a spec" message.
- If spec already exists: "View Spec" and "Generate New Spec" buttons.

### Spec Configuration Modal

When PM clicks "Generate Spec," a modal with:

**Scope selector:** Two cards — "MVP" (rocket icon) and "Full" (document icon).

**Audience selector:** Three cards — "AI Agent" (robot icon), "Engineer" (person icon), "Mixed" (both icon).

**Custom instructions:** Expandable text area for technical context.

**Generate button.**

### Spec Page (NEW — `/specs/{id}`)

Similar layout to Brief page.

**Layout:**
- Header with title, version, scope badge, audience badge, status.
- Version selector dropdown.
- Sections as cards with regenerate and edit buttons.
- Export buttons: "Export Markdown" and "Export for Cursor."
- Evidence trail highlights: user stories with linked customer quotes.

### Generation Progress

Same as briefs — sections appear as they complete, progress indicator.

### Theme Dashboard Updates

- Theme cards with brief AND spec show "Spec Ready" badge linking to the spec.

### Chat Integration

- "Generate a spec for [theme name]" triggers generation if brief + evaluation exist.
- "Show me the user stories for [theme name]" returns user stories from spec.
- New tool functions: `generate_spec_tool`, `get_spec_section_tool`.

---

## Export Formats

### Standard Markdown

Clean markdown with all sections for Notion, Google Docs, Confluence, or Slack.

### Cursor-Optimized Format

Condensed, highly structured markdown matching our phase spec format:
- Goal and Done-means at the top
- Evidence summary with customer counts and priority score
- Database tables as markdown tables
- API endpoints as markdown tables
- Acceptance criteria as checkboxes
- Non-negotiable rules
- Evidence trail linking every requirement to customer quotes

This format is the product's ultimate output — a spec an AI agent can execute with every requirement traced to a real customer.

---

## LLM Configuration for Specs

| Setting | Dev (Ollama) | Production (Anthropic) |
|---------|-------------|----------------------|
| Model | llama3.2:3b | claude-sonnet-4-20250514 |
| Temperature | 0.3 | 0.3 |
| Max tokens per section | 1500 | 2000 |
| Timeout per section | 60 seconds | 30 seconds |

**New environment variables:**

| Variable | Dev Value | Prod Value | Purpose |
|----------|-----------|------------|---------|
| SPEC_LLM_MODEL | llama3.2:3b | claude-sonnet-4-20250514 | Model for spec generation |
| SPEC_MAX_SECTION_TOKENS | 1500 | 2000 | Max tokens per section response |
| SPEC_TEMPERATURE | 0.3 | 0.3 | Temperature for spec generation |

---

## Testing

### test_spec_service.py
1. Generate spec requires brief with solution evaluation — returns error if no evaluation.
2. Generate spec creates record with status="generating" and queues task.
3. Get spec returns all sections when completed.
4. Get current spec returns latest version.
5. New spec for same brief increments version.
6. Spec filters by org_id (multi-tenant isolation).
7. Export markdown returns clean formatted string.
8. Export Cursor format returns structured spec matching phase-spec format.
9. Spec from another org returns 404.

### test_spec_generation_service.py
1. Generate all sections produces 8 sections in correct order.
2. User stories include acceptance criteria.
3. User stories reference pain points from solution evaluation.
4. Functional requirements reference user stories (US-1, US-2, etc.).
5. Technical guidance varies by target_audience (ai_agent is more prescriptive).
6. MVP scope produces fewer user stories than full scope.
7. Data model section includes table/column suggestions.
8. API contracts include endpoint paths and request/response shapes.
9. Testing section includes acceptance-criteria-based verification.
10. Custom instructions are injected into technical sections.
11. Evidence trail links requirements to customer quotes.

### test_spec_routes.py
1. POST /specs/generate creates spec and returns spec_id.
2. POST /specs/generate without solution evaluation returns 400.
3. GET /specs/{id} returns spec with sections.
4. GET /specs/{id}/status returns generation progress.
5. GET /specs/brief/{brief_id} returns all versions.
6. GET /specs/theme/{theme_id} returns all specs for theme.
7. PATCH /specs/{id}/sections/{key} edits section.
8. POST /specs/{id}/sections/{key}/regenerate regenerates section.
9. GET /specs/{id}/export/markdown returns clean markdown.
10. GET /specs/{id}/export/cursor returns Cursor-optimized format.
11. Spec from another org returns 404.

---

## Non-Negotiable Rules for This Phase

Everything from Phases 1-7 still applies, plus:

1. **Every requirement has evidence.** User stories and functional requirements must reference the pain points, feature gaps, or customer quotes they address.
2. **Scope setting actually changes the output.** MVP specs are noticeably shorter and more focused than full specs.
3. **Audience setting actually changes the output.** AI agent specs are prescriptive and structured. Engineer specs are advisory and readable.
4. **Sections build on each other.** Requirements reference user stories. Technical guidance references requirements. API contracts reference data model.
5. **Edited sections are preserved.** Regenerating other sections doesn't touch edited ones.
6. **Cursor export format matches our spec format.** Same structure, same level of detail as the phase specs throughout this project.
7. **Spec generation requires a solution evaluation.** Don't generate specs for themes where the PM hasn't evaluated a solution.
8. **Export produces clean output.** No debug artifacts, no JSON blobs, no generation metadata in the exported file.

---

## What NOT to Build

- Direct integration with Cursor/Claude Code (future — PM copies the spec manually)
- Direct push to Jira/Linear/GitHub Issues (future)
- Spec collaboration/comments (future)
- Automatic spec updates when themes change (future)
- Cost or timeline estimation (future)

---

## Acceptance Criteria

Phase 8 is complete when ALL of these are true:

- [ ] PM can click "Generate Spec" on a completed brief with solution evaluation
- [ ] Configuration modal lets PM choose scope (MVP/Full) and audience (AI Agent/Engineer/Mixed)
- [ ] Custom instructions field accepts additional context
- [ ] Spec generation runs as background task with progress visible
- [ ] All 8 sections generate with meaningful content
- [ ] Executive summary is concise and clear
- [ ] Background & evidence cites real customer quotes
- [ ] User stories follow standard format with acceptance criteria
- [ ] User stories reference specific pain points from customer evidence
- [ ] Functional requirements reference user stories (US-1, etc.)
- [ ] Technical guidance matches the target audience
- [ ] Data model section suggests concrete table/column changes
- [ ] API contracts specify endpoints with request/response shapes
- [ ] Testing section includes verification steps tied to acceptance criteria
- [ ] MVP scope produces fewer, focused user stories vs full scope
- [ ] Evidence trail links every requirement to customer feedback
- [ ] PM can regenerate individual sections
- [ ] PM can edit sections inline
- [ ] Versioning works (new spec for same brief = new version)
- [ ] Standard markdown export is clean and shareable
- [ ] Cursor-optimized export matches our phase spec format
- [ ] Brief page shows "Generate Spec" button (disabled without solution eval)
- [ ] Spec page renders all sections with proper formatting
- [ ] Chat can trigger spec generation and query spec content
- [ ] Multi-tenant: specs scoped to org_id
- [ ] All Phase 8 tests pass
- [ ] All Phase 1-7 tests still pass
- [ ] **THE FULL LOOP WORKS:** Upload feedback → extract signals → cluster themes → prioritize → generate brief → evaluate solution → generate spec → export for Cursor

---

## How to Give This to Cursor

1. Save this file as `D:\LinkedIn\Week4\docs\PHASE_8_SPEC.md`
2. Open Cursor's chat and type:

> Read `docs/PHASE_8_SPEC.md`. This is the spec for Phase 8 — the final phase. The `.cursorrules` file still applies. Do NOT start building yet. Create a detailed implementation plan first: list every file you will create or modify, what each contains, the order of work, and dependencies. Present the full plan and wait for my approval.

3. Review the plan. Approve or push back.
4. Let Cursor build.
5. Run through acceptance criteria.

---

## After Phase 8

**The product is feature-complete for v1.**

The full 8-layer pipeline is live:

```
Layer 1: Data Ingestion (CSV, Manual, Slack)
Layer 2: Signal Extraction (LLM: pain points, urgency, sentiment, topics)
Layer 3: Customer Enrichment (smart matching, PM review queue)
Layer 4: Clustering & Prioritization (embeddings, HDBSCAN, 5-factor scoring)
Layer 5: Conversational Layer (RAG chat, tool functions)
Layer 6: Evidence Briefs (7-section briefs, solution evaluation)
Layer 7: Agent-Ready Specs (8-section specs, evidence trail, Cursor export)
```

**What comes next (post-v1):**
- Deploy to production (cloud hosting, Claude API for all LLM calls)
- Invite beta PMs to use the product with real data
- Add integrations: Intercom, Zendesk, HubSpot, Salesforce
- Add PDF export for briefs and specs
- Add spec push to Jira/Linear/GitHub Issues
- Add streaming responses for chat
- Add team features: shared briefs, spec reviews, comments
- Optimize: model fine-tuning, better clustering, faster embeddings
- Build the portfolio site and demo video
- Start charging