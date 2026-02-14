# Cursor for PMs

An AI-powered tool that transforms raw customer feedback into prioritized, evidence-backed, agent-ready product specifications.

## Prerequisites

- Docker and Docker Compose
- Git
- **Python 3.10** (for local backend development and tests; this project uses only 3.10)

## Setup

1. Clone the repository and enter the project directory.

2. The project includes a `.env` file with working development values. If you need to customize, copy from `.env.example` and edit:
   ```bash
   cp .env.example .env
   ```

3. Start all services:
   ```bash
   docker-compose up --build
   ```

4. **Phase 3 (Signal extraction):** If using Ollama for local LLM extraction, start the Ollama service and pull the model once:
   ```bash
   docker-compose up -d ollama
   docker-compose exec ollama ollama pull llama3.2:3b
   ```
   Set in `.env`: `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://ollama:11434`, `OLLAMA_MODEL=llama3.2:3b`. For production, use `LLM_PROVIDER=anthropic` and set `ANTHROPIC_API_KEY` and `ANTHROPIC_EXTRACTION_MODEL`.

5. **Migrations:** Run once so the database schema is up to date:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```
   If that fails with "already exists" (e.g. the DB was created earlier or by another process), sync Alembic only—without applying migrations—by running `docker-compose exec backend alembic stamp head`. After that, `upgrade head` will report "already at head" and stay in sync.

6. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API docs (Swagger): http://localhost:8000/docs

7. Run backend tests (**recommended: inside the backend container**, where all deps including pgvector and sentence-transformers are installed):
   ```bash
   docker-compose exec backend pytest app/tests -v
   ```
   Or run tests in a one-off container (builds and runs with same Dockerfile):
   ```bash
   docker-compose run --rm backend pytest app/tests -v
   ```
   (Paths are relative to the container working directory `/app`.) Phase 5+ dependencies are only guaranteed in the Docker image; running pytest on the host requires a full local install of `backend/requirements.txt`.

## Local Python environment (single version)

This project uses **Python 3.10 only**. A virtualenv at the repo root keeps one consistent environment.

- **Create venv (once):**
  ```bash
  py -3.10 -m venv .venv
  .venv\Scripts\pip install -r backend\requirements.txt
  ```
- **Run backend tests locally** (Postgres and Redis must be running, e.g. `docker-compose up -d db redis`):
  - Ensure `TEST_DATABASE_URL` matches your Postgres (e.g. `.env.test` with `postgresql://postgres:postgres@127.0.0.1:5432/cursor_for_pms` to use Docker’s exposed DB). Credentials must match `POSTGRES_USER` / `POSTGRES_PASSWORD` in docker-compose.
  ```bash
  .venv\Scripts\python -m pytest backend\app\tests -v
  ```
  Or from the `backend` folder:
  ```bash
  cd backend
  ..\.venv\Scripts\python -m pytest app/tests -v
  ```
- **Use this Python for everything** in this repo (run server, migrations, scripts):  
  `\.venv\Scripts\python.exe` or activate first:  
  `\.venv\Scripts\Activate.ps1` then `python` / `pip` / `pytest`.

## Acceptance criteria

See [docs/PHASE_1_SPEC.md](docs/PHASE_1_SPEC.md) for Phase 1 acceptance criteria.
