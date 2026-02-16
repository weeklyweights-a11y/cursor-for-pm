# Documentation index

This folder contains everything you need to understand what the project does and how it is built—in **plain English**, so anyone (not only developers) can follow along.

---

## Start here

| Document | What it is |
|----------|------------|
| [**PHASES_OVERVIEW.md**](PHASES_OVERVIEW.md) | What each phase of the project does: the plan and the architecture, in simple language. **Includes flow charts** (pipeline overview and phase-by-phase flow). |
| [**ARCHITECTURE.md**](ARCHITECTURE.md) | How the whole system is put together: frontend, backend, worker, database, and AI. **Includes diagrams** (system architecture and data flow). |

---

## Phase-by-phase details

Each phase has a **plan** (what we set out to do) and **architecture** (how it works and what we use).

| Phase | Plan & architecture |
|-------|----------------------|
| Phase 1 — Foundation | [phase_01_foundation.md](phase_01_foundation.md) |
| Phase 2 — Data ingestion | [phase_02_data_ingestion.md](phase_02_data_ingestion.md) |
| Phase 3 — Signal extraction | [phase_03_signal_extraction.md](phase_03_signal_extraction.md) |
| Phase 4 — Enrichment & clustering | [phase_04_enrichment_clustering.md](phase_04_enrichment_clustering.md) |
| Phase 5 — Prioritization | [phase_05_prioritization.md](phase_05_prioritization.md) |
| Phase 6 — Briefs & evidence | [phase_06_briefs_evidence.md](phase_06_briefs_evidence.md) |
| Phase 7 — Solution design | [phase_07_solution_design.md](phase_07_solution_design.md) |
| Phase 8 — Specs & export | [phase_08_specs_export.md](phase_08_specs_export.md) |

---

## Technical specs (for builders)

| Document | What it is |
|----------|------------|
| [**PHASE_1_SPEC.md**](PHASE_1_SPEC.md) | Full technical specification for Phase 1 (acceptance criteria, stack, database, API). Used to implement the foundation. |

---

## Sample data

| File | What it is |
|------|------------|
| **sample_feedback.csv** | Example customer feedback rows. Upload this in the app to test the pipeline. |
| **sample_customers.csv** | Example customer list (domain, company name, segment). Upload after feedback so the app can match feedback to customers. |

Use these together to run a full test: upload feedback, then customers, then run extraction and clustering.
