# Phase 7 — Solution design (plan and architecture)

Plain-English description of how we go from a brief to a scoped solution.

---

## Plan

**Goal:** Turn a brief (and its theme) into a **solution**: what to build at a product level—scope, user stories, flows, edge cases—before we write the final engineer-facing spec.

We wanted:

- The system to **generate** a solution from the brief and the theme’s feedback (and product context).
- The solution to include **scope** (what’s in, what’s out), **user stories**, and **flows** or edge cases where useful.
- The PM to **refine** the solution (through edits or conversation) before we move to the agent-ready spec in Phase 8.

---

## Architecture (how it works)

**Data model:**

- **Solutions** (or equivalent) linked to a theme and/or brief. We store scope, user stories, and any flow or edge-case text. This can be one blob per solution or structured sections (e.g. scope, user_stories, flows).

**Generation:**

- When the PM asks for a solution (or when moving from brief to spec), we call the **LLM** with the brief content, the theme’s feedback summary, and product context. The prompt asks for scope, user stories, and optionally flows. We parse and save the result so Phase 8 can use it as input for the spec.

**Refinement:**

- The PM can edit the solution in the UI or discuss it in chat. We persist the latest version so the spec generator (Phase 8) always uses the current scope and stories.

**Why a separate “solution” step:**

- It keeps the brief (problem and evidence) separate from the “what we will build” (solution). The spec then translates the solution into a very structured, implementation-ready format for engineers or AI coding tools.
