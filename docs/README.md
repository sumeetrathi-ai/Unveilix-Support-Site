# Unveilix Support — build package

Hand this whole folder to Claude in VS Code (Claude Code). Three files:

1. **`BUILD_PROMPT.md`** — paste this as your first message to Claude in VS Code,
   or say: *"Read BUILD_PROMPT.md and build this end to end, following the spec
   and mockup. Test everything yourself."* This is the instruction set.
2. **`UNVEILIX_SUPPORT_SPEC.md`** — the technical source of truth (data model,
   API, roles, tenant isolation, Docker, seed data). Claude follows this.
3. **`unveilix-support.html`** — the UI/UX mockup. Claude opens it as the visual
   target and ports it to React.

## How to run it

1. Put these three files in an empty folder and open that folder in VS Code.
2. Make sure **Docker Desktop is running**.
3. In Claude Code, send: *"Read BUILD_PROMPT.md and begin Phase 0."*
4. Let it work through the phases. It will scaffold the repo, build the FastAPI
   backend + PostgreSQL (in Docker) + React frontend, write and **run** its own
   pytest suite (including the tenant-isolation tests), seed the database, and
   verify the whole thing end to end with `docker compose up`.
5. When it's done it will give you: start command, seeded login credentials,
   and the passing test summary.

## What you get
- The project is scaffolded from the **official FastAPI full-stack template**
  (`fastapi/full-stack-fastapi-template`) — so it starts from a vetted, current
  skeleton (Docker Compose, JWT auth, Alembic, pytest, React+Vite+TS) rather
  than hand-rolled structure. Claude adapts that template to our domain.
- FastAPI + PostgreSQL (Docker) backend with JWT auth and strict tenant isolation.
- React (Vite + TS) frontend matching the mockup: client report flow with screen
  recording + screenshot upload, and the Unveilix team triage board.
- A docker-compose stack that runs the lot with one command.
- An automated test suite proving isolation works.

## The two guarantees baked into the spec
- A client org can never see another org's tickets (enforced at the DB query
  layer, with tests).
- The Unveilix team sees all orgs and can filter by org.
- Within an org, every user sees all of that org's tickets.

## If you want to change scope
Edit `UNVEILIX_SUPPORT_SPEC.md` before handing it over — that's the file Claude
treats as authoritative. The "Out of scope for v1" section (§10) lists things
intentionally deferred (email/Slack alerts, knowledge base, SSO, real SLAs).
