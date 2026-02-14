# Phase 1: Foundation Setup

> **Goal:** A running app skeleton with authentication and multi-tenant organization support. No business logic. Just the foundation that every future phase builds on.
>
> **Done means:** You can open the app in a browser, sign up, log in, see an empty dashboard with a three-column layout (sidebar, main area, chat placeholder), and hit a health check API that confirms the database is connected.

---

## Context for the AI Agent

You are building a production SaaS web app called "Cursor for PMs." This is Phase 1 of 8. You are setting up the project skeleton. Do not build any business features yet — no feedback ingestion, no LLM calls, no clustering, no dashboards with data. Just authentication, organization management, and the app shell.

This is a multi-tenant B2B SaaS product. Every user belongs to an organization. Every database query that touches org-specific data must filter by `org_id`. This is a non-negotiable security rule from day one.

**Project root:** `D:\LinkedIn\Week4`

---

## Tech Stack (Use Exactly These)

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend framework | FastAPI (Python 3.12) | AI-heavy backend, Python-native ML libraries in later phases |
| Frontend framework | React + TypeScript + Vite | Standard modern web stack |
| CSS | Tailwind CSS | Utility-first, fast to build with |
| Database | PostgreSQL 16 with pgvector extension | Relational + vector search for later phases |
| ORM | SQLAlchemy 2.x | Mature Python ORM, works well with Alembic |
| Migrations | Alembic | Schema versioning, auto-generation from models |
| Cache / Queue broker | Redis 7 | Will be used for Celery job queue in Phase 2 |
| Auth | JWT (python-jose + passlib bcrypt) | Stateless auth, standard for SPAs |
| Config | pydantic-settings | Type-safe env var loading |
| Logging | Python logging + python-json-logger | Structured JSON logs |
| Testing | pytest + httpx | Standard Python testing |
| Containerization | Docker + Docker Compose | Local dev environment matching production |

Do not substitute any of these. Do not add libraries not listed here unless absolutely necessary, and if you do, explain why.

---

## Project Structure

Create this folder structure. Follow it exactly. Do not add extra folders or files beyond what is described below.

**Root level:**
- Docker Compose file for orchestrating all services
- Environment variable file (and an example version without real secrets)
- Gitignore file
- README with setup instructions

**`backend/` directory:**
- Dockerfile for the Python backend
- Requirements file listing all Python dependencies
- Alembic configuration and migrations directory
- `app/` package containing:
  - **`models/`** — SQLAlchemy ORM models. One file per table. A shared base model mixin that gives every table `id` (UUID), `created_at`, and `updated_at` automatically.
  - **`schemas/`** — Pydantic models for request validation and response serialization. One file per domain (auth, organization).
  - **`services/`** — Business logic functions. No HTTP concerns, no direct session creation. Receives a DB session as a parameter. One file per domain.
  - **`routes/`** — FastAPI route handlers. Thin: validate input via Pydantic, call the service, return the response. One file per domain, plus a health check route.
  - **`middleware/`** — Auth dependency that extracts and validates JWT from the Authorization header.
  - **`utils/`** — Password hashing, JWT creation/decoding, structured logging setup.
  - **`tests/`** — Test files with shared fixtures (test client, test database session, helper to create a test user with token).
  - Main app file that creates the FastAPI instance, adds CORS middleware, and includes all routers.
  - Config file that loads all environment variables using pydantic-settings.
  - Database file that sets up SQLAlchemy engine, session factory, and the `get_db` dependency.

**`frontend/` directory:**
- Dockerfile for the React dev server
- Package file with all JS dependencies
- Vite config, TypeScript config, Tailwind config, PostCSS config
- `src/` containing:
  - **`api/`** — Axios client instance with auth interceptor (attaches token, redirects on 401). Typed API functions for auth and org endpoints.
  - **`context/`** — React AuthContext that provides user state, login/signup/logout functions, and checks for existing token on app load.
  - **`pages/`** — LoginPage, SignupPage, DashboardPage. Each is a full page component.
  - **`components/`** — Layout (three-column: sidebar, main, chat placeholder), PrivateRoute (redirects unauthenticated users to login), LoadingSpinner.
  - **`types/`** — TypeScript interfaces for User, Organization, auth responses.
  - App component with React Router setup.
  - Entry point and CSS file with Tailwind imports.

**`docs/` directory:**
- This spec file
- Later phases will add their specs here

---

## Docker Compose Services

Define exactly 4 services:

**1. `db` — PostgreSQL 16**
- Expose port 5432.
- Create the pgvector extension on first startup (use an init script mounted into the container's entrypoint directory).
- Persist data with a named volume so it survives container restarts.
- Add a healthcheck that confirms Postgres is accepting connections.

**2. `redis` — Redis 7 Alpine**
- Expose port 6379.
- No persistence needed for development.

**3. `backend` — FastAPI**
- Build from the backend Dockerfile.
- Expose port 8000.
- Depends on `db` and `redis` (wait for db healthcheck).
- Mount the backend source code as a volume so code changes reflect without rebuilding.
- Load environment variables from the .env file.
- Run uvicorn with hot-reload enabled.

**4. `frontend` — React (Vite)**
- Build from the frontend Dockerfile.
- Expose port 3000.
- Mount the frontend source code as a volume for hot-reload.
- Depends on backend.

---

## Environment Variables

All configuration must come from environment variables. Nothing hardcoded anywhere in the codebase.

Define these variables in the .env file:

**Database:** Postgres user, password, database name, host (use the Docker service name), port, and a full connection URL.

**Redis:** Connection URL.

**JWT:** Secret key (use a long random string for dev), algorithm (HS256), token expiration in minutes (default 1440 = 24 hours).

**App:** Environment name (development), debug flag (true), backend port (8000), frontend port (3000), backend URL (http://localhost:8000), frontend URL (http://localhost:3000).

**LLM (placeholder for later phases):** Provider name (ollama), Ollama base URL (http://ollama:11434). These won't be used in Phase 1 but set them up now so the config is ready.

Also create an `.env.example` file with the same keys but placeholder values instead of real secrets.

---

## Database Models

### Base Model Mixin

Every table in the system inherits from a shared base that provides:
- `id` — UUID primary key, auto-generated.
- `created_at` — Timestamp with timezone, set automatically on insert, never null.
- `updated_at` — Timestamp with timezone, set automatically on insert and update, never null.

### Organizations Table

| Column | Type | Rules |
|--------|------|-------|
| id | UUID | Primary key (from base) |
| name | String, max 255 | Required |
| slug | String, max 255 | Required, unique, indexed. Used in URLs. |
| created_at | Timestamp | From base |
| updated_at | Timestamp | From base |

Has a one-to-many relationship with users.

### Users Table

| Column | Type | Rules |
|--------|------|-------|
| id | UUID | Primary key (from base) |
| email | String, max 255 | Required, unique, indexed |
| name | String, max 255 | Required |
| hashed_password | String, max 255 | Required. Store bcrypt hash, never plain text. |
| org_id | UUID | Foreign key to organizations.id, required, indexed |
| role | String, max 50 | Default "admin", required |
| is_active | Boolean | Default true |
| created_at | Timestamp | From base |
| updated_at | Timestamp | From base |

Has a many-to-one relationship with organization.

---

## API Endpoints

All endpoints are prefixed with `/api/v1/`.

### Health Check

**`GET /api/v1/health`** — No authentication required.
- Check that the database connection is alive.
- Return status "healthy" with app version and environment name if everything is fine.
- Return status "unhealthy" with HTTP 503 if the database is unreachable.

### Authentication

**`POST /api/v1/auth/signup`** — No authentication required.
- Accepts: email, password (minimum 8 characters), name, organization name.
- Creates a new organization (generate a URL-friendly slug from the org name; if slug already exists, append random characters to make it unique).
- Creates a new user with hashed password, linked to the new organization.
- Returns the user, organization, and a JWT access token.
- If email already exists, return HTTP 400 with a clear error message.

**`POST /api/v1/auth/login`** — No authentication required.
- Accepts: email, password.
- Validates credentials.
- Returns the user and a JWT access token.
- If email not found or password wrong, return HTTP 401. Do not reveal which one was wrong (security best practice).

**`GET /api/v1/auth/me`** — Requires authentication.
- Returns the current authenticated user's profile.
- If token is missing, invalid, or expired, return HTTP 401.

### Organization

**`GET /api/v1/organization`** — Requires authentication.
- Returns the current user's organization.
- Must filter by the org_id from the authenticated user's token. A user must never be able to see another organization's data.

**`PATCH /api/v1/organization`** — Requires authentication.
- Accepts: updated organization name (optional).
- Updates only the current user's organization.

---

## Authentication Flow

### JWT Token

The JWT token payload must contain:
- `sub` — The user's ID (UUID as string).
- `org_id` — The user's organization ID (UUID as string).
- `exp` — Expiration timestamp.

The auth middleware dependency must:
1. Extract the Bearer token from the Authorization header.
2. Decode and validate the JWT.
3. Load the user from the database using the user ID from the token.
4. Verify the user exists and is active.
5. Make the user object available to the route handler.
6. Return HTTP 401 for any failure (missing token, invalid token, expired token, inactive user).

---

## Frontend Pages and Layout

### Login Page
- A centered card with email and password fields and a submit button.
- Link to signup page ("Don't have an account? Sign up").
- On successful login, redirect to /dashboard.
- On error, show the error message to the user.

### Signup Page
- A centered card with name, email, password, and organization name fields and a submit button.
- Link to login page ("Already have an account? Log in").
- Client-side validation: all fields required, email format, password at least 8 characters.
- On successful signup, redirect to /dashboard.

### Dashboard Page
- Uses the Layout component.
- Shows a welcome message with the user's name and organization name.
- The main content area is intentionally empty. It will be filled in later phases.
- This page exists to prove the full auth flow works end-to-end.

### Layout Component

A three-column layout that will be used by every authenticated page:

**Left sidebar (fixed width, roughly 250px):**
- App name or logo at the top.
- Navigation links (only "Dashboard" for now, more will be added in later phases).
- User's name and a logout button at the bottom.

**Center main area (flexible width, takes remaining space):**
- Renders whatever page content is passed as children.

**Right panel (fixed width, roughly 320px):**
- A placeholder panel with a light gray background.
- Shows text like "AI Assistant" at the top and "Chat will be available soon" in the center.
- This is where the conversational AI sidebar will live in Phase 6.

### Auth Context

A React context provider that wraps the entire app and provides:
- Current user state (null if not logged in).
- Functions to login, signup, and logout.
- An `isLoading` state that is true while the app checks for an existing token on first load.
- On app load: if a token exists in localStorage, validate it by calling GET /auth/me. If valid, set the user. If invalid, clear the token.

### Private Route

A route wrapper that checks if the user is authenticated. If not, redirect to /login. If still loading (checking token), show a loading spinner.

### API Client

An Axios instance configured with:
- Base URL pointing to the backend API.
- A request interceptor that adds the JWT token from localStorage to every request.
- A response interceptor that clears the token and redirects to /login if any request returns 401.

---

## Backend Tests

Write tests for:

**Auth tests:**
1. Signup with valid data returns 200 with user, organization, and token.
2. Signup with an email that already exists returns 400.
3. Login with valid credentials returns 200 with token.
4. Login with wrong password returns 401.
5. Login with nonexistent email returns 401.
6. GET /auth/me with valid token returns the user.
7. GET /auth/me without a token returns 401.
8. GET /auth/me with an expired or invalid token returns 401.

**Organization tests:**
1. GET /organization with valid token returns the user's organization.
2. PATCH /organization updates the name successfully.
3. A user cannot access or modify an organization they don't belong to. (Create two separate users in two separate orgs, verify user A cannot see user B's org.)

**Health test:**
1. GET /health returns "healthy" when database is connected.

Use a test database or transaction rollback so tests don't pollute each other.

---

## Non-Negotiable Rules for This Phase

These rules apply to every line of code written in this phase and all future phases:

1. **No hardcoded secrets.** Every configurable value comes from environment variables loaded through pydantic-settings.
2. **No print() statements.** All logging uses Python's logging module with the JSON formatter. Log meaningful events: server start/stop, signup, login, errors.
3. **No raw SQL.** All database access goes through SQLAlchemy ORM with parameterized queries.
4. **No business logic in routes.** Routes validate input, call a service function, and return the result. That's it.
5. **Multi-tenant isolation.** Every query that touches org-specific data must include `org_id` filtering. Test this.
6. **Type everything.** Type hints on all Python function signatures. Pydantic models for all API contracts. TypeScript interfaces for all frontend data shapes.
7. **Handle errors.** Every service function that can fail must raise a clear, specific exception. Routes catch these and return appropriate HTTP status codes with descriptive error messages.
8. **No TODO comments that defer critical logic.** If something needs to work, make it work. If something is genuinely for a later phase, mark it as a placeholder with a comment referencing which phase will implement it.

---

## What NOT to Build

Do not build any of these. They come in later phases:

- Feedback ingestion, CSV upload, Slack integration (Phase 2)
- LLM integration, Ollama container, extraction (Phase 3)
- Customer matching, enrichment (Phase 4)
- Embeddings, clustering, themes, prioritization (Phase 5)
- Chat functionality, conversational AI (Phase 6)
- Brief generation, solution design (Phase 7)
- Spec generation, export (Phase 8)
- Celery workers or background jobs (Phase 2)

If you find yourself building something not described in this spec, stop. You are going off-track.

---

## Acceptance Criteria

Phase 1 is complete when ALL of these are true:

- [ ] `docker-compose up --build` starts all 4 services (db, redis, backend, frontend) without errors
- [ ] The pgvector extension is installed in the database
- [ ] Alembic migration creates the organizations and users tables with correct columns, types, indexes, and foreign keys
- [ ] `GET /api/v1/health` returns healthy status confirming database connection
- [ ] A new user can sign up via `POST /api/v1/auth/signup` and receives a JWT token
- [ ] An existing user can log in via `POST /api/v1/auth/login` and receives a JWT token
- [ ] `GET /api/v1/auth/me` returns the current user when a valid token is provided
- [ ] `GET /api/v1/auth/me` returns 401 when no token, invalid token, or expired token is provided
- [ ] `GET /api/v1/organization` returns only the authenticated user's organization
- [ ] A user from Org A cannot access Org B's data (multi-tenant isolation verified by test)
- [ ] Frontend login page loads in the browser
- [ ] Frontend signup page loads in the browser
- [ ] User can sign up through the frontend, land on the dashboard, and see their name and org name
- [ ] Dashboard shows three-column layout: left sidebar with nav, center main area, right chat placeholder
- [ ] User can log out from the dashboard and is redirected to login
- [ ] FastAPI Swagger docs are accessible at /docs
- [ ] All backend tests pass
- [ ] No hardcoded secrets anywhere in the codebase
- [ ] No print() statements anywhere — only structured logging
- [ ] Every org-related query filters by org_id

---

## How to Give This to Cursor

1. Save this file as `D:\LinkedIn\Week4\docs\PHASE_1_SPEC.md`
2. Open the project folder in Cursor.
3. Open Cursor's chat and type:

> Read the file `docs/PHASE_1_SPEC.md`. This is the spec for Phase 1 of the project. Build everything described in this spec, following the structure, tech stack, and rules exactly. Work through it section by section. After completing each major section, briefly confirm what you built before moving on. Do not add features, files, or libraries not described in the spec. When you are done, run through the acceptance criteria and confirm each one passes.

4. Let Cursor work. If it asks questions, answer them. If it adds something not in the spec, tell it to remove it and follow the spec.
5. When Cursor says it is done, check the acceptance criteria yourself.

---

## After Phase 1

Once all acceptance criteria pass, come back for Phase 2: Data Ingestion. That phase will add the feedback_items table, CSV upload (sync + async with batch tracking), manual input form, Slack integration, and the Celery worker setup.
