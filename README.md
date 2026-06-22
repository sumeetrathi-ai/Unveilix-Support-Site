# Unveilix Support

A multi-tenant bug-tracking web app for **Unveilix**. Client organizations report bugs in
their Unveilix instance (with screen recordings + screenshots) and track status; the Unveilix
product team triages every bug across every client on one board.

Built on the official [`fastapi/full-stack-fastapi-template`](https://github.com/fastapi/full-stack-fastapi-template)
and adapted to this domain. **FastAPI + SQLModel + PostgreSQL** backend, **React + Vite + TS**
frontend, all orchestrated with **Docker Compose**.

> The two guarantees, enforced at the **database query layer** (not just the UI) and covered
> by automated tests:
> 1. **Strict tenant isolation** — a client org can never see, query, or open another org's
>    tickets. Out-of-tenant access returns `404` (never leaks existence).
> 2. **The Unveilix team sees everything** across all orgs and can filter by org. Within an
>    org, every user sees all of that org's tickets.

---

## Prerequisites

- **Docker Desktop** running (Postgres runs inside Docker — no local Postgres needed).
- Ports **8000** (API), **5174** (web), **5433** (db) free on the host.

## Run it (one command)

```bash
docker compose up --build       # or: make up
```

This builds the images, starts **db → prestart → backend → frontend**, runs **migrations**
and the **idempotent seed** automatically, and leaves the app usable. Then open:

- **Web app:** http://localhost:5174
- **API docs (Swagger):** http://localhost:8000/docs
- **API base:** http://localhost:8000/api

Stop with `docker compose down` (keeps data) or `make fresh` (deletes the data volume).

> Optional tooling (Adminer DB UI, Traefik, mailcatcher) is gated behind Compose profiles
> and does **not** start by default. Enable with `docker compose --profile tools up`.

## Seeded accounts

The seed creates **one client org (Carnera)** plus 12 accounts, and prints a no-secrets
summary (`docker compose logs prestart`). All Carnera client users share the pilot password
`(SEED_CLIENT_PASSWORD in .env)`; all Unveilix admins share `(SEED_ADMIN_PASSWORD in .env)`. Passwords are Argon2-hashed and
never printed. There is **no demo ticket data** — the board/list start empty until users
report bugs.

| Family | Logins | Password | Role | Sees |
|--------|--------|----------|------|------|
| Carnera **clients** | `bhabani@`, `sumeet@`, `piyush@`, `ankita@`, `rajesh@`, `remigius@` `getcarnera.com` | `(SEED_CLIENT_PASSWORD in .env)` | client_user | Carnera only |
| Unveilix **admins** | `bhabani@`, `sumeet@`, `piyush@`, `ankita@`, `rajesh@`, `remigius@` `unveilix.ai` | `(SEED_ADMIN_PASSWORD in .env)` | admin | all orgs |

After login the app redirects by family: **clients → Report a bug**, **team → Dashboard**.

> **Security:** these shared pilot passwords are fine for a controlled internal pilot but must
> be rotated (and force-changed on first login) before any external client uses the system.
> Override them locally without editing source via `SEED_CLIENT_PASSWORD` /
> `SEED_ADMIN_PASSWORD` in `.env` (keep real values out of any public repo). `sumeet@unveilix.ai`
> is also the bootstrap superuser, so keep `FIRST_SUPERUSER_PASSWORD` == the admin seed password.

## Running the tests

```bash
make test            # full suite (67 tests) in a throwaway Dockerized Postgres
make test-isolation  # just the 10 tenant-isolation cases
```

`make test` builds the backend image (tests are baked in), wipes any local DB, applies the
schema, runs `pytest` in a fresh container, and tears the throwaway stack down again. It
includes the **10 tenant-isolation cases** (spec §5), auth tests, and a full ticket-lifecycle
test. **All 67 pass.**

## Architecture

```
.
├── compose.yml / compose.override.yml   # db, prestart (migrate+seed), backend, frontend (+ profiled extras)
├── Makefile                             # up / down / fresh / logs / seed / test
├── backend/
│   └── app/
│       ├── models.py          # SQLModel: Organization, User, Ticket, Attachment, Comment, Activity + enums
│       ├── api/
│       │   ├── deps.py        # get_ticket_scope + scoped_ticket_or_404 (THE tenant chokepoint), role guards
│       │   └── routes/        # auth, tickets, attachments, organizations, dashboard, users, login
│       ├── crud.py            # ticket creation, reference gen, activity logging, summary builders
│       ├── seed.py            # idempotent demo seed (orgs/users/tickets)
│       └── alembic/versions/  # single squashed initial migration
└── frontend/
    └── src/                   # React + Vite + TS, plain CSS (dark-navy theme), TanStack Query
        ├── api.ts             # typed fetch client (bearer token)
        ├── components/        # Sidebar, TicketDrawer, Kanban, ScreenRecorder
        └── pages/             # Login, Report, MyTickets, Dashboard, Board, AllTickets, Clients
```

**How tenant isolation is enforced (the important bit):** every ticket-reading endpoint
builds its query through `app/api/deps.py::get_ticket_scope(current_user)`, which returns a
SQLAlchemy condition — `Ticket.organization_id == current_user.organization_id` for client
users, or unrestricted for the Unveilix team (honoring an optional `?organization_id=`
filter). Single-ticket lookups go through `scoped_ticket_or_404`, which returns `404` when a
ticket is outside the caller's tenant. A DB `CHECK` constraint additionally guarantees client
users always have an org and team users never do. Internal comments are stripped from
client-family responses.

**Key flows:** clients report bugs with auto-captured environment (browser/OS/module/etc. —
never raw query text or results), optional screen recording (`getDisplayMedia` +
`MediaRecorder` → `.webm`) and screenshots; the team triages on a six-column Kanban
(`new → deferred → in_development → in_testing → deployed → closed`), assigns engineers,
overrides priority, and adds internal notes.

## API quick reference (base `/api`)

| Method | Path | Who | Purpose |
|--------|------|-----|---------|
| POST | `/auth/login` | all | login → `{access_token, token_type, user}` |
| GET | `/auth/me` | authed | current user |
| GET | `/tickets` | scoped | list (filters: status, priority, module, assignee_id, organization_id, q) |
| GET | `/tickets/board` | team | tickets grouped by status (Kanban) |
| GET | `/tickets/{id}` | scoped | detail (internal comments only for team) |
| POST | `/tickets` | client/team | create (priority from severity, UVX-#### ref) |
| PATCH | `/tickets/{id}` | team | status / priority / assignee |
| POST | `/tickets/{id}/comments` | scoped | comment (clients: public only) |
| POST | `/tickets/{id}/attachments` | scoped | upload screenshot/recording |
| GET | `/attachments/{id}` | scoped | stream a file |
| GET | `/organizations` | team | orgs with open/deployed counts |
| POST | `/organizations` | admin | onboard org |
| GET | `/dashboard/stats` | team | KPIs |
| GET | `/users/team` | team | assignable team members |

## Notable decisions / deviations from the original spec

Full log in [`PROGRESS.md`](PROGRESS.md). Highlights:

- **Ports remapped** (db→5433, web→5174, adminer→8081) because the host already runs the real
  Unveilix product dev stack on 5432/5173/8080. The API stays on 8000.
- **Frontend** uses plain CSS (the mockup ported verbatim) + a tiny built-in router + a hand
  written typed `fetch` client, keeping TanStack Query. The template's
  TanStack-Router/Tailwind/shadcn/generated-client layers were dropped for a faithful,
  low-risk match to the mockup. The two hard rules are backend-enforced, so this is a pure UI
  choice.
- **Auth hashing** is Argon2 (the template's `pwdlib` default) rather than bcrypt — stronger,
  and legacy bcrypt hashes are still verified/upgraded transparently.
- Added `GET /api/users/team` (team-only) so the UI can populate the assignee dropdown.

## Out of scope for v1 (per spec §10)

Email/Slack notifications, knowledge base, SSO, real SLA policies (a stub is used), duplicate
detection, file virus scanning, and pagination beyond simple `limit`/`offset`.

---

The original build brief, technical spec, and UI mockup are preserved under [`docs/`](docs/).
