# Unveilix Support — Technical Specification

> Source of truth for the Unveilix Support application. The build prompt
> (`BUILD_PROMPT.md`) tells the agent *how* to work; this file defines *what*
> to build. When in doubt, this document wins over the mockup; the mockup
> (`unveilix-support.html`) wins on visual/UX questions.

---

## 1. Product summary

Unveilix is a multi-tenant conversational BI product sold to client
organizations. **Unveilix Support** is the bug-tracking web app where:

1. **Client users** report bugs in their Unveilix instance (with optional
   screen recording + screenshots), and track status.
2. **The Unveilix product team** triages every bug across every client on one
   board, assigns engineers, and moves tickets through a lifecycle.

### Two hard rules (non-negotiable)

- **Strict tenant isolation.** A client user can only ever see, query, or open
  tickets belonging to their own organization. There is no client-facing
  endpoint, query, or response that can return another org's data. Enforce this
  at the **database query layer on every request**, not just in the UI.
- **The Unveilix team sees everything**, across all organizations, and can
  filter by organization.

### Within an org
Every user in a client org sees **all** of that org's tickets (not just the
ones they personally raised). No per-user filtering inside an org.

---

## 2. Roles

There are two role *families*. Keep them simple.

| Role           | Family   | Can see                              | Can do |
|----------------|----------|--------------------------------------|--------|
| `client_user`  | client   | All tickets for **their own org**    | Create tickets, comment (public), upload attachments, view status |
| `agent`        | unveilix | **All tickets, all orgs**            | Everything client can + change status/priority/assignee, internal notes, manage clients |
| `admin`        | unveilix | **All tickets, all orgs**            | Everything `agent` can + onboard/disable orgs, create users |

> For the first build, `agent` and `admin` can share one UI. Gate org/user
> management behind `admin`. Both are "Unveilix team".

The `family` field on the user (`client` vs `unveilix`) is what drives tenant
isolation. A `unveilix`-family user bypasses the org filter; a `client`-family
user is always pinned to their `organization_id`.

---

## 3. Data model (PostgreSQL)

> **Template note:** the project is scaffolded from
> `fastapi/full-stack-fastapi-template` (see BUILD_PROMPT Phase 0), which uses
> **SQLModel**, not raw SQLAlchemy. Implement these tables as SQLModel models.
> The columns, constraints, enums, and relationships below are authoritative
> regardless of ORM. The template already provides a `User` model and auth —
> extend the `User` with the fields below rather than creating a parallel users
> table.

Use UUID primary keys (`gen_random_uuid()`). All timestamps `TIMESTAMPTZ`,
default `now()`. Use snake_case. Add `created_at` / `updated_at` to every table.

### `organizations`
| column | type | notes |
|--------|------|-------|
| id | uuid PK | |
| name | text not null unique | e.g. "Pennrose" |
| plan | text not null default 'growth' | enum-like: `growth`, `enterprise` |
| is_active | boolean not null default true | disabling blocks all that org's users |
| created_at, updated_at | timestamptz | |

### `users`
| column | type | notes |
|--------|------|-------|
| id | uuid PK | |
| organization_id | uuid FK -> organizations.id, nullable | NULL for unveilix-family users |
| email | text not null unique | login id |
| full_name | text not null | |
| hashed_password | text not null | bcrypt/passlib |
| family | text not null | `client` or `unveilix` |
| role | text not null | `client_user`, `agent`, `admin` |
| is_active | boolean not null default true | |
| created_at, updated_at | timestamptz | |

> Constraint: if `family='client'` then `organization_id` must be NOT NULL.
> If `family='unveilix'` then `organization_id` must be NULL.

### `tickets`
| column | type | notes |
|--------|------|-------|
| id | uuid PK | |
| reference | text not null unique | human id e.g. `UVX-1042`; generate sequentially |
| organization_id | uuid FK -> organizations.id NOT NULL | **the tenant key** |
| reporter_id | uuid FK -> users.id NOT NULL | |
| title | text not null | "What happened?" |
| description | text | steps & details |
| module | text not null | enum below |
| severity | text not null | client-facing, enum below |
| priority | text not null | engineering, P1-P4, derived from severity (overridable by team) |
| status | text not null default 'new' | lifecycle enum below |
| assignee_id | uuid FK -> users.id, nullable | a unveilix-family user |
| environment | jsonb | auto-captured diagnostics (see §6) |
| created_at, updated_at | timestamptz | |
| closed_at | timestamptz nullable | set when status -> closed |

### `attachments`
| column | type | notes |
|--------|------|-------|
| id | uuid PK | |
| ticket_id | uuid FK -> tickets.id NOT NULL | |
| kind | text not null | `screenshot` or `recording` |
| filename | text not null | |
| content_type | text not null | e.g. image/png, video/webm |
| size_bytes | bigint | |
| storage_path | text not null | relative path on disk volume |
| created_at | timestamptz | |

### `comments`
| column | type | notes |
|--------|------|-------|
| id | uuid PK | |
| ticket_id | uuid FK -> tickets.id NOT NULL | |
| author_id | uuid FK -> users.id NOT NULL | |
| body | text not null | |
| is_internal | boolean not null default false | **internal notes are NEVER returned to client users** |
| created_at | timestamptz | |

### `activity` (audit trail / timeline)
| column | type | notes |
|--------|------|-------|
| id | uuid PK | |
| ticket_id | uuid FK -> tickets.id NOT NULL | |
| actor_id | uuid FK -> users.id NOT NULL | |
| action | text not null | e.g. `created`, `status_changed`, `assigned`, `priority_changed`, `commented`, `attachment_added` |
| detail | jsonb | e.g. `{"from":"new","to":"in_development"}` |
| created_at | timestamptz | |

### Enums (store as text + validate in app layer with Python `Enum`)

- **module**: `conversational_query`, `charts`, `datasource`, `agent_view`,
  `rbac`, `audit_log`, `other`
- **severity** (client picks): `blocks_work`, `major`, `minor`, `suggestion`
- **priority** (engineering): `P1`, `P2`, `P3`, `P4`
- **status**: `new`, `deferred`, `in_development`, `in_testing`, `deployed`, `closed`

### Severity → priority default mapping
| severity | default priority |
|----------|------------------|
| blocks_work | P1 |
| major | P2 |
| minor | P3 |
| suggestion | P4 |

Team can override priority after creation; store the override and log it in
`activity`.

---

## 4. API (FastAPI)

Base path `/api`. JSON everywhere. Auth via JWT bearer token.

### Auth
- `POST /api/auth/login` — body `{email, password}` → `{access_token, token_type, user}`.
  `user` includes `id, full_name, email, family, role, organization_id`.
- `GET /api/auth/me` — returns the current user.
- (No public signup. Users are seeded / created by admin.)

### Tenant-scoping dependency (CRITICAL)
Implement a FastAPI dependency, e.g. `get_ticket_scope(current_user)`, that
returns a SQLAlchemy filter:
- if `current_user.family == 'client'` → `Ticket.organization_id == current_user.organization_id`
- if `current_user.family == 'unveilix'` → no org restriction (but honor an
  optional `?organization_id=` query filter)

**Every ticket-reading endpoint MUST apply this scope.** Do not build any
endpoint that reads tickets without it.

### Tickets
- `GET /api/tickets` — list with filters: `status`, `priority`, `module`,
  `assignee_id`, `organization_id` (team only), `q` (search title/reference).
  Always scoped. Returns summary fields + counts of attachments/comments.
- `GET /api/tickets/{id}` — full detail incl. attachments, public comments
  (and internal comments **only if** `family=='unveilix'`), activity timeline,
  environment. Scoped — 404 (not 403) if out of tenant, to avoid leaking existence.
- `POST /api/tickets` — client or team creates. Body: `title, description,
  module, severity, environment`. Server sets `organization_id` from the
  reporter (client) or from body (team, must specify org), derives `priority`
  from severity, generates `reference`, writes `created` activity.
- `PATCH /api/tickets/{id}` — **team only.** Update `status`, `priority`,
  `assignee_id`. Each change writes an `activity` row. Setting status=closed
  sets `closed_at`.
- `GET /api/tickets/board` — team only. Returns tickets grouped by status for
  the Kanban (respects same filters).

### Attachments
- `POST /api/tickets/{id}/attachments` — multipart upload. Scoped (client can
  only attach to own org's ticket). Save file to a Docker volume path; store
  metadata row. Enforce: max size (e.g. 50 MB), allowed types (`image/png`,
  `image/jpeg`, `video/webm`, `video/mp4`).
- `GET /api/attachments/{id}` — stream the file. Scoped.

### Comments
- `POST /api/tickets/{id}/comments` — body `{body, is_internal}`. Client users
  may **only** post `is_internal=false`; reject `is_internal=true` from clients.
- Comments come back inside the ticket detail; never expose internal comments
  to client family.

### Clients / users (admin only)
- `GET /api/organizations` — team only; list with open/deployed counts.
- `POST /api/organizations` — admin; onboard org.
- `POST /api/users` — admin; create user (client or team).
- `GET /api/dashboard/stats` — team only; KPIs: open count, breaching-SLA count
  (stub SLA = open P1 older than 24h, P2 older than 72h), deployed-last-7d,
  median resolution time.

### Error contract
- 401 unauthenticated, 403 wrong role for the action, 404 not found / out of
  tenant scope, 422 validation. JSON `{detail: "..."}`.

---

## 5. Tenant isolation — explicit test cases the agent MUST write & pass

Write these as automated tests (pytest). They are the acceptance gate.

1. Client user from Org A `GET /api/tickets` → response contains **only** Org A
   tickets; zero Org B tickets present.
2. Client user from Org A `GET /api/tickets/{orgB_ticket_id}` → **404**.
3. Client user from Org A `POST /comments {is_internal:true}` → **rejected**
   (forced to false or 422).
4. Client user `PATCH /api/tickets/{id}` (status change) → **403**.
5. Client user `GET /api/tickets/{own_ticket}` → internal comments **absent**
   from response.
6. Unveilix agent `GET /api/tickets` → sees Org A + Org B.
7. Unveilix agent `GET /api/tickets?organization_id=<A>` → only Org A.
8. Created ticket from `blocks_work` severity → priority defaults to `P1`.
9. New ticket auto-generates a unique `UVX-####` reference.
10. Attachment upload by client to another org's ticket → **404/403**.

---

## 6. Auto-captured environment (`environment` jsonb)

On the client report screen, capture and send with the ticket (no raw query
text or result values — privacy rule from Unveilix audit-log design):
`{ browser, browser_version, os, screen, unveilix_module, datasource_type,
agent_run_id, reported_url }`. Frontend derives browser/OS from
`navigator.userAgent`; the rest are form/context values. Display read-only in
the team detail drawer.

---

## 7. Frontend (React)

- **Stack**: React + Vite + TypeScript, comes from the template. The official
  template ships **Chakra UI** + TanStack Query/Router and an auto-generated API
  client. Keep TanStack Query/Router and the generated client. For styling, you
  may use Chakra or plain CSS/CSS-modules — **whatever reproduces the mockup's
  dark-navy theme (§9) most faithfully.** The mockup is the visual target, not
  Chakra defaults. Do not pull in a second heavy component library.
- **Routes**:
  - `/login`
  - Client family: `/report` (default), `/tickets` (my org's list), `/tickets/:id`
  - Unveilix family: `/dashboard` (default), `/board`, `/tickets`, `/tickets/:id`,
    `/clients`
  - A landing role is implicit from the logged-in user; no role chooser in the
    real app (that was a demo affordance). After login, redirect by family.
- **Screen recording**: use `navigator.mediaDevices.getDisplayMedia` +
  `MediaRecorder` to produce a `.webm` blob, then upload via the attachments
  endpoint. Show a live timer; allow stop; preview before submit.
- **Screenshot upload**: file input + drag/drop; preview thumbnails.
- **Detail drawer / page**: status + assignee editable for team; read-only
  status for clients; attachments (image inline, video with player); activity
  timeline; comment box (internal toggle for team only).
- **Reuse the mockup** (`unveilix-support.html`) as the visual spec: layout,
  spacing, colors, Kanban columns, KPI cards, severity picker, status pills.
  Port it to real components wired to the API. Keep the exact six status
  columns and the plain-language severity picker.

---

## 8. Infra / Docker

> **Template note:** the official template already provides a working
> `docker-compose.yml` (db + backend + frontend + Adminer + Traefik), Alembic,
> and a pytest harness. Reuse it. You mainly need to: point it at our project
> name, add an `uploads` volume for attachments, replace the seed/initial-data
> script with ours, and ensure migrations + seed run on startup. Don't rebuild
> compose from scratch if the template's works.

Single `docker compose up` brings up everything:
- `db`: `postgres:16`, env for db/user/password, named volume for data, healthcheck.
- `api`: FastAPI (uvicorn), depends_on db healthy, mounts an `uploads` volume
  for attachments, runs migrations + seed on start, exposes `:8000`.
- `web`: React dev server (Vite) on `:5173`, proxies `/api` to `api`.
- Provide `.env.example`. Provide `Makefile` or scripts: `make up`, `make seed`,
  `make test`.
- DB migrations: Alembic (or `Base.metadata.create_all` for v1 if simpler — but
  prefer Alembic).
- **Seed script** creates: 3 orgs (Pennrose [enterprise], MQOL [growth],
  Northwind Health [enterprise]); a client user per org (e.g.
  `will.flynn@pennrose.com`); two unveilix users (`sumeet@unveilix.ai` admin,
  `adit@unveilix.ai` agent); and ~10 sample tickets spread across orgs/statuses
  matching the mockup data so the UI looks alive immediately. Print seeded
  login credentials at the end.

---

## 9. Visual tokens (must match mockup)

```
--bg:#0A0F1F  --bg-2:#0E1428  --bg-3:#141B33
--line:#1F2944  --ink:#EAF0FF  --ink-2:#9AA7C7  --ink-3:#5E6B8C
--accent:#5B8CFF (blue)  --accent-2:#22D3A7 (teal/deployed)
--violet:#9C7BFF  --amber:#F4B740 (testing)  --rose:#FF6B81 (P1/critical)
radius 14px; font Inter; mono JetBrains Mono
```
Status colors: new=blue, deferred=grey, in_development=violet,
in_testing=amber, deployed=teal, closed=slate.
Priority chips: P1 rose, P2 amber, P3 blue, P4 grey.

---

## 10. Out of scope for v1 (note as TODO, do not build)
Email/Slack notifications, knowledge base, SSO, real SLA policies, duplicate
detection, file virus scanning, pagination beyond a simple limit/offset.
Leave clean extension points.
