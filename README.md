# Cursor for PMs

**Turn customer feedback into clear product specs—without the guesswork.**

Cursor for PMs is a web app that takes messy, real-world feedback (from emails, CSVs, support tickets, or typed-in notes), figures out what customers really want, groups similar ideas into themes, and writes structured specs that you or an AI coding assistant can use to build the right thing.

---

## What problem does it solve?

Product managers get feedback everywhere: Slack, email, spreadsheets, support tools. Turning that into a clear “what to build and why” is slow and manual. This app:

- **Collects** feedback from multiple places (upload a CSV, paste text, or connect Slack later).
- **Understands** each piece—what’s the pain, how urgent, positive or negative.
- **Groups** similar feedback into themes so you see patterns, not just one-off comments.
- **Prioritizes** themes using your goals (e.g. focus on enterprise, or on high-urgency items).
- **Writes** evidence-backed briefs and specs you can hand to engineering or to an AI coding tool.

Everything runs in Docker so you can try it locally without messing with your machine.

---

## What you need to run it

- **Docker** and **Docker Compose** (so we can run the app, database, and AI model in containers).
- **Git** (to clone the project).

That’s it for a first run. Optionally you can use **Python 3.10** on your machine if you want to run tests or scripts outside Docker.

---

## How to run the app

1. **Clone the repo** and open the project folder in a terminal.

2. **Environment file**  
   The project may include a `.env` file. If not, copy from `.env.example` and edit if needed:
   ```bash
   cp .env.example .env
   ```

3. **Start everything**
   ```bash
   docker compose up --build
   ```
   This starts the database, Redis, backend API, frontend, and worker. The first time it may take a few minutes to build and pull images.

4. **Start Ollama (for AI extraction)**  
   The app uses an AI model to read feedback and extract meaning. We run that model inside Docker too:
   ```bash
   docker compose up -d ollama
   docker compose exec ollama ollama run llama3:8b
   ```
   The second command downloads the model once; you can cancel after it finishes. Then restart backend and worker so they use Ollama:
   ```bash
   docker compose restart backend worker
   ```

5. **Database migrations** (run once)
   ```bash
   docker compose exec backend alembic upgrade head
   ```
   If you see “already exists” errors, you can run:
   ```bash
   docker compose exec backend alembic stamp head
   ```
   then try `upgrade head` again.

6. **Open the app**
   - **App (website):** http://localhost:3000  
   - **API docs:** http://localhost:8000/docs  

7. **Sign up** in the app, then you can add product context, upload feedback (e.g. the sample CSV in `docs/`), and run extraction and clustering.

---

## What’s inside the project?

| Part | What it does |
|------|----------------|
| **Frontend** | React + TypeScript app: login, dashboard, upload feedback, view themes, briefs, and specs. |
| **Backend** | FastAPI (Python): handles users, feedback, themes, briefs, specs, and calls to the AI model. |
| **Worker** | Background jobs: runs AI extraction on each feedback item, enrichment, clustering, and spec generation. |
| **Database** | PostgreSQL with pgvector: stores users, feedback, themes, briefs, specs, and vector embeddings. |
| **Redis** | Used as a message queue so the worker can process jobs in the background. |
| **Ollama** | Runs the AI model (e.g. Llama) inside Docker so the app can “read” and structure feedback. |

All of this is described in more detail in the **docs** folder: phase-by-phase plan and architecture in plain English.

---

## Running tests

From the project root:

```bash
docker compose exec backend pytest app/tests -v
```

Paths are relative to the backend app inside the container (`/app`).

---

## Documentation

- **[docs/README.md](docs/README.md)** — Index of all documentation.
- **[docs/PHASES_OVERVIEW.md](docs/PHASES_OVERVIEW.md)** — What each phase does and how it fits together (plain English).
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — High-level picture: how the app is built and how data flows.
- **docs/phase_01_*.md through phase_08_*.md** — Per-phase plan and architecture.
- **[docs/PHASE_1_SPEC.md](docs/PHASE_1_SPEC.md)** — Original detailed technical spec for Phase 1 (foundation).

Sample data to try the full flow:

- **docs/sample_feedback.csv** — Example feedback rows (upload in the app).
- **docs/sample_customers.csv** — Example customer list (upload for enrichment).

---

## License and use

This project is for learning and evaluation. Use it as a reference or starting point for your own product tooling.
