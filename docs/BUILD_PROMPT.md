# BUILD PROMPT — Unveilix Support (read this first)

You are building a production-quality bug-tracking web application called
**Unveilix Support**, end to end, on your own. Work autonomously: plan, build,
run, test, fix, and verify without waiting for me between steps. Only stop to
ask me something if you hit a genuine blocker you cannot resolve yourself.

## Inputs you have
1. **`UNVEILIX_SUPPORT_SPEC.md`** — the technical source of truth (data model,
   API, roles, tenant isolation, infra, seed data). Follow it precisely.
2. **`unveilix-support.html`** — the interactive UI/UX mockup. This is the
   visual + interaction target. Open it, study the layout, theme, Kanban,
   severity picker, KPI cards, detail drawer, and screen-recording flow, and
   reproduce that look and feel in React. The HTML is a demo (it has a role
   chooser and fake data); the real app replaces those with real auth and a
   real API, but the visual design must match.

## Environment (already on my machine)
- Docker Desktop is installed and running.
- I will run the app with Docker Compose. PostgreSQL must run **inside Docker**
  (do not assume a local Postgres). Backend = Python **FastAPI**. Frontend =
  **React** (Vite + TypeScript).

## The two rules you must never break
1. **Strict tenant isolation** — a client org can NEVER see another org's
   tickets, by any endpoint, query, or response. Enforce at the DB query layer
   on every request via the scoping dependency described in the spec.
2. **The Unveilix team sees all orgs** and can filter by org.
Within an org, every user sees all of that org's tickets.

---

## How to work (process)

Work in phases. After each phase, **run it and prove it works** before moving
on. Keep a running `PROGRESS.md` in the repo where you check off each phase and
note anything you changed from the spec and why.

### Phase 0 — Plan & scaffold (start from a vetted template, don't hand-roll)

**Do not build the project skeleton by hand.** Bootstrap from a maintained
full-stack template, then adapt it to our spec. This gives us a tested Docker
Compose setup, JWT auth, Alembic, and a pytest harness out of the box.

**Template choice — evaluate these two, then pick one and tell me why:**

1. **`fastapi/full-stack-fastapi-template`** (official, by FastAPI's author —
   *recommended default*). It is the best-maintained option and already ships
   exactly the stack we want: FastAPI + PostgreSQL + Docker Compose + JWT auth +
   Alembic + pytest + a React/TypeScript/Vite frontend with login, protected
   routes, and an auto-generated API client. **Caveats to adapt to, not fight:**
   - It is generated with **Copier**, not Cookiecutter:
     `pipx run copier copy https://github.com/fastapi/full-stack-fastapi-template unveilix-support --trust`
     (Copier is the modern successor to Cookiecutter and is the correct tool
     here; if `copier` isn't installed, use `pipx run copier ...` or
     `pip install copier`.)
   - Its ORM is **SQLModel** (SQLAlchemy + Pydantic), not raw SQLAlchemy. Use
     SQLModel — translate the spec's table definitions into SQLModel models.
     This is a better fit than raw SQLAlchemy anyway.
   - Its frontend components use **Chakra UI**. You may keep Chakra or replace
     with plain CSS/CSS-modules — **whichever lets you match the mockup's exact
     dark-navy theme (spec §9) most faithfully.** The visual target is the
     mockup, not Chakra's defaults. Don't let the template's styling override
     ours; theme it to match.
   - It has an `items` example resource. **Replace `items` with our `tickets`
     domain** (and add `organizations`, `attachments`, `comments`, `activity`).
     Delete the items example once tickets work.

2. **`Buuntu/fastapi-react`** (a true Cookiecutter:
   `cookiecutter https://github.com/Buuntu/fastapi-react`). Simpler and uses
   raw SQLAlchemy, which maps 1:1 to our spec, but it's **older** (react-router
   v5, Create-React-App rather than Vite, react-admin). Only choose this if the
   official template causes real trouble; if you pick it, upgrade the frontend
   to Vite.

**Decision rule:** default to the official `fastapi/full-stack-fastapi-template`
unless you hit a concrete blocker, because it's current and matches our stack.
Record which template you chose and why in `PROGRESS.md`.

**After generating from the template:**
- Run the template's own stack once (`docker compose up`) to confirm the
  baseline works *before* you change anything. Note the result in `PROGRESS.md`.
- Then adapt: rename the project/stack vars to `unveilix-support`, strip the
  example `items` resource, and keep the parts we want (auth, users, Docker,
  Alembic, pytest harness, frontend login + protected routes + generated
  client).
- Keep the resulting tree close to the template's conventions rather than
  forcing the exact folder names from earlier drafts — match the template, and
  note the final structure in `PROGRESS.md`.
- Write `PROGRESS.md` with the phase checklist.

> Everything else in this prompt (the two rules, the data model, the tenant
> isolation tests, the seed data, the mockup as visual target) stays the same.
> The template gives you the skeleton; our spec defines the domain on top of it.

### Phase 1 — Database & models
- Define SQLAlchemy models for all tables in the spec (§3). UUID PKs,
  timestamps, the family/organization constraint, enums validated in app.
- Set up Alembic and generate the initial migration.

### Phase 2 — Backend API
- Build all endpoints in spec §4 with JWT auth (passlib + python-jose).
- Implement the `get_ticket_scope` tenant dependency and apply it to **every**
  ticket-reading endpoint. This is the most important code in the app — comment
  it clearly.
- Derive priority from severity; generate `UVX-####` references; write
  `activity` rows on create/status/assign/priority/comment.
- Internal comments must never be serialized into a client-family response.
- File upload/stream endpoints save to the uploads volume with type/size limits.

### Phase 3 — Tests (do not skip — this is your acceptance gate)
- Use **pytest** with a throwaway Postgres (testcontainers, or a separate test
  DB in compose, or SQLite only if Postgres-specific features aren't needed —
  prefer Postgres for fidelity).
- Implement **all 10 tenant-isolation test cases from spec §5**, plus auth tests
  (login, /me, wrong-role 403) and a happy-path ticket-lifecycle test
  (create → assign → move through statuses → close, asserting activity rows).
- **Run the tests. They must all pass.** If any fail, fix the code (not the
  test) until green. Paste the passing test summary into `PROGRESS.md`.

### Phase 4 — Seed data
- Write the seed script from spec §8: 3 orgs, client users, two team users, ~10
  tickets across orgs/statuses mirroring the mockup. Make it idempotent.
- Print the seeded login credentials at the end of the seed run.

### Phase 5 — Frontend
- Scaffold Vite + React + TS. Port the mockup to real components, wired to the
  API. Match the dark-navy theme tokens exactly (spec §9).
- Implement: login; client `/report` (with **working screen recording** via
  getDisplayMedia + MediaRecorder, screenshot upload, severity picker,
  auto-captured environment) and `/tickets` list scoped to the user's org;
  team `/dashboard` (KPIs), `/board` (six-column Kanban), `/tickets` (filterable
  table with org filter), shared `/tickets/:id` detail (team can edit
  status/assignee + internal notes; client read-only status, public comments
  only), and `/clients`.
- After login, redirect by user family (client → /report, unveilix → /dashboard).
  No demo role chooser.

### Phase 6 — Compose & end-to-end verification
- Finish `docker-compose.yml` so `docker compose up` brings up db + api + web,
  runs migrations + seed, and the app is usable at the web port.
- Verify end to end yourself:
  - `docker compose up` succeeds; all services healthy.
  - Hit the API health endpoint and a couple of real endpoints with curl using
    a token from a seeded user; confirm a client token cannot fetch another
    org's ticket (expect 404) and a team token can (expect 200). Paste the curl
    output into `PROGRESS.md`.
  - Load the frontend, log in as the seeded client and as the seeded team user,
    and confirm the two experiences and the isolation behave as specified.
- Write the root `README.md`: prerequisites, `docker compose up`, seeded
  credentials, how to run tests (`make test`), and a short architecture note.

---

## Self-verification checklist (must be true before you tell me you're done)
- [ ] `docker compose up` starts db + api + web with no manual steps.
- [ ] Migrations + seed run automatically; seeded credentials printed/in README.
- [ ] `make test` (pytest) runs and **all tests pass**, including the 10
      tenant-isolation cases.
- [ ] Curl proof of isolation pasted in `PROGRESS.md` (client→other org = 404,
      team→any org = 200).
- [ ] Client login lands on Report; can submit a bug with a screenshot and a
      screen recording; sees only their org's tickets.
- [ ] Team login lands on Dashboard; Kanban shows six correct columns; org
      filter works; can change status/assignee/priority and add an internal
      note that the client never sees.
- [ ] UI visually matches the mockup's theme and layout.
- [ ] `README.md` and `PROGRESS.md` are complete.

## Working style
- Prefer running commands and reading output over guessing. When something
  fails, read the error, fix it, re-run.
- Make small, sensible decisions yourself and record them in `PROGRESS.md`;
  don't pause to ask about trivia (library choices, file names, minor UX).
- Do ask me only if: a decision materially changes scope, or an external
  dependency genuinely can't be resolved.
- Keep secrets out of git; use `.env` (provide `.env.example`).
- When finished, give me: how to start it, the seeded credentials, the test
  result summary, and anything you deviated from the spec on and why.

Begin with Phase 0 now.
