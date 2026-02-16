# Phase 1 — Foundation (plan and architecture)

Plain-English description of what we built and how it works.

---

## Plan

**Goal:** A working app skeleton that anyone can open in a browser.

We wanted:

- People to **sign up** and **log in**.
- Each user to belong to an **organization** (company/team).
- After login, a **dashboard** with a simple layout: sidebar, main area, and a placeholder for chat.
- A **health check** so we can confirm the app is connected to the database.

No feedback, no AI, no themes—just the foundation. Every feature we add later will assume “user is logged in” and “data belongs to this organization.”

---

## Architecture (how it works)

**What you see (frontend):**

- A **React** app (with TypeScript and Vite) that runs in the browser.
- **Tailwind CSS** for styling so we can build the layout quickly.
- Pages: **Login**, **Signup**, **Dashboard**.
- A **layout** with three areas: sidebar (navigation), main content, and a chat placeholder.
- The app stores a **token** after login and sends it with every request so the server knows who is asking.

**What runs on the server (backend):**

- **FastAPI**: a Python web framework that handles login, signup, and “who am I?” requests.
- **PostgreSQL**: the database. We store **users** (email, hashed password, name) and **organizations** (name, slug). Every user is linked to one organization.
- **Redis**: used later for background jobs; in Phase 1 we just have it running.
- **JWT**: instead of storing “logged in” state on the server, we give the browser a signed token. The frontend sends that token with each request; the backend checks it and knows the user and org.

**How it’s all run:**

- **Docker Compose** starts four things: the database, Redis, the backend (API), and the frontend (React dev server). So one command (“docker compose up”) starts the whole stack.

**Security rule from day one:**

- Every request that touches data is checked for a valid token and **organization**. We never show or change data from another org.
