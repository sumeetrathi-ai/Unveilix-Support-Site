# Unveilix Support — Build Progress

> Running log of the phased build (per `docs/BUILD_PROMPT.md`). For a granular,
> step-by-step resume journal see [`docs/memory.md`](docs/memory.md).

## Template choice (Phase 0)

**Chosen: the official `fastapi/full-stack-fastapi-template`** (generated with Copier,
`--vcs-ref=HEAD`).

**Why:** It is current and ships exactly our target stack with no fighting required:
FastAPI + PostgreSQL + Docker Compose + JWT auth + Alembic + pytest on the backend, and
React + Vite + TypeScript + TanStack Query/Router + an auto-generated API client on the
frontend. The alternative (`Buuntu/fastapi-react`) is older (react-router v5, CRA instead
of Vite, react-admin) and would need a frontend upgrade to Vite before we even start. The
official template's only "caveats" (Copier not Cookiecutter; SQLModel not raw SQLAlchemy;
Chakra UI; an `items` example resource) are all easy to adapt to and are noted below. No
blocker was hit, so per the prompt's decision rule we stayed on the recommended default.

**Adaptations the template requires (tracked):**
- ORM is SQLModel → translate the spec's tables to SQLModel models (Phase 1).
- API prefix is `/api/v1` → change to `/api` per spec §4 (Phase 2).
- Replace the `items` example resource with our `tickets` domain (+ organizations,
  attachments, comments, activity); delete `items` once tickets work.
- Theme the frontend to the mockup's dark-navy tokens (spec §9) rather than Chakra defaults.

## Phase checklist

- [x] **Phase 0 — Plan & scaffold.** Template generated; baseline confirmed working:
      `GET /api/v1/utils/health-check/` → 200; superuser login → JWT; `GET /users/me`
      → 200. Frontend baseline build verified separately. _(see D5 for port remap)_
- [x] **Phase 1 — Database & models.** SQLModel models for all 6 tables (organizations,
      users, tickets, attachments, comments, activity) with UUID PKs, TIMESTAMPTZ
      created/updated, JSONB env/detail, enums-as-text. Single squashed Alembic migration
      `b8691bbba9a0`. Verified: tables created, the `ck_user_family_organization` CHECK
      constraint is **enforced at the DB layer** (psql rejected client-without-org and
      unveilix-with-org), seeded admin valid, login/`/me` OK.
- [x] **Phase 2 — Backend API.** All spec §4 endpoints built (auth, tickets list/board/
      detail/create/update, comments, attachments upload/stream, organizations, dashboard).
      `get_ticket_scope` applied on every ticket read; `scoped_ticket_or_404` returns 404
      out-of-tenant. Priority-from-severity, `UVX-####` refs, activity logging, internal-
      comment hiding, upload type/size limits. **Verified by a 20-check curl smoke test:
      PASS=20 FAIL=0** (all isolation behaviors + role guards + lifecycle).
- [x] **Phase 3 — Tests.** `make test` → **67 passed** (49 adapted template tests + 18 new
      domain tests) in a throwaway Dockerized Postgres. Includes all 10 tenant-isolation
      cases (spec §5), auth tests (login/me/401/403), and the create→assign→status-walk→
      close lifecycle asserting the activity timeline. See "Test results" below.
- [x] **Phase 4 — Seed data.** `backend/app/seed.py` (idempotent, **upsert by email**).
      **Baseline updated 2026-06-22: all demo data removed.** Seeds exactly one client org
      (**Carnera**, enterprise, active), 6 Carnera client users (`@getcarnera.com`,
      `client_user`) and 6 Unveilix admins (`@unveilix.ai`, `admin`). No demo tickets/
      comments/attachments/activity. Passwords are Argon2-hashed and **never printed**; the
      seed prints a no-secrets account summary table. Runs automatically in `prestart.sh`;
      re-run via `make seed`. See "Seed baseline" below.
- [x] **Phase 5 — Frontend.** Mockup ported to React (Vite+TS), plain CSS with the exact
      §9 dark-navy tokens, wired to `/api`. Login (redirect by family), client `/report`
      (severity picker, **screen recording** via getDisplayMedia+MediaRecorder, screenshot
      upload, auto-env), client `/tickets` + `/tickets/:id`, team `/dashboard` (KPIs),
      `/board` (six-column Kanban), `/tickets` (filter table incl. org filter), shared
      `/tickets/:id` drawer (team edits status/assignee/priority + internal notes; client
      read-only + public comments), `/clients`. Verified by a **headless Playwright smoke**
      (client sees 4 Pennrose tickets, no status select, no internal comments; team sees 10
      tickets, 6 Kanban columns, editable drawer, 3 clients) + screenshots. Builds via Vite
      and the Bun Docker image. See D5/D6 deviations.
- [x] **Phase 6 — Compose & e2e.** `docker compose up --build` brings up db+api+web (no manual
      steps; migrations+seed auto-run), all healthy. Curl isolation proof captured (below).
      Both client and team logins verified end-to-end via headless Playwright against the
      **Dockerized** frontend (:5174). README written. (Fixed a prestart/backend parallel
      build race by removing prestart's duplicate `build:`.)

## Decisions & deviations from spec
- **D1** Template = official full-stack-fastapi-template (rationale above).
- **D2** `copier` installed in an isolated `.copier-venv/` (build tool only; the app's own
  deps install inside Docker). Honors "don't pollute the system".
- **D3** Moved the three input docs + original README into `docs/` so the scaffold could be
  laid out flat at the repo root (so `docker compose up` works from the opened folder).
- **D4** Tests run **inside** the backend container (template pytest harness), wrapped by
  `make test` — avoids requiring a local `uv`/Python env.
- **D5** Local host ports remapped (db→5433, frontend→5174, adminer→8081; backend stays
  8000) because the machine already runs the real Unveilix dev stack on 5432/5173/8080.
  Non-core compose services gated behind profiles (`tools`, `test`) so a bare
  `docker compose up` runs only db+prestart+backend+frontend. Added `app-uploads` volume.
- **D6 (frontend)** Built the UI with **plain CSS** (porting the mockup's stylesheet) + a
  tiny built-in history router + a hand-written typed `fetch` client, keeping **TanStack
  Query**. Dropped the template's TanStack-Router/Tailwind/shadcn/generated-client layers
  (and switched the frontend `build` to `vite build`, no separate `tsc`) — chosen for a
  faithful, low-risk match to the mockup and to avoid regenerating a client against the
  changed API. The two hard rules are backend-enforced, so this is purely a UI choice.
- **D7** Added `GET /api/users/team` (team-only) so the UI can populate the assignee
  dropdown (the template's `GET /users` is superuser-only). Added frontend origins
  (5174/5180) to `BACKEND_CORS_ORIGINS`.

## Self-verification checklist (BUILD_PROMPT) — ALL TRUE

- [x] `docker compose up` starts db + api + web with no manual steps. _(single command,
      verified from a clean `down -v`; all services healthy)_
- [x] Migrations + seed run automatically; seeded credentials printed (`docker compose logs
      prestart`) and in README.
- [x] `make test` runs and all tests pass (**67 passed**), incl. the 10 tenant-isolation cases.
- [x] Curl proof of isolation pasted below (client→other org = 404, team→any org = 200).
- [x] Client login → Report; sees only their org's tickets (4 Pennrose). Screenshot upload +
      submit verified end-to-end; screen recording implemented (`getDisplayMedia` +
      `MediaRecorder` → `.webm`, uploaded via the attachments endpoint) and a seeded recording
      plays in the drawer. _(Note: live `getDisplayMedia` capture is browser-native and works
      in a secure context / localhost; it can't be driven by the headless smoke, which is why
      the recording-playback path is what's asserted automatically.)_
- [x] Team login → Dashboard; Kanban six columns; org filter; edit status/assignee/priority;
      internal note hidden from client (isolation test #5 + UI smoke confirm).
- [x] UI matches the mockup theme/layout. _(screenshots reviewed: dashboard, report, drawer)_
- [x] README.md and PROGRESS.md complete.

## Deployment prep (2026-06-22): pluggable storage + Render migrate/seed

### Task 1 — Backblaze B2 (S3-compatible) storage backend  ✅ implemented
Uploads/downloads now go through a pluggable storage layer selected by `STORAGE_BACKEND`
(`local` | `s3`), so the same code runs on local disk in dev and Backblaze B2 in prod.

- **New `backend/app/core/storage.py`** — a small `StorageBackend` interface
  (`save(key,data,content_type) -> key`, `open_stream(key)`, `exists(key)`, `delete(key)`)
  with two impls:
  - `LocalStorage(base_dir=UPLOADS_DIR)` — filesystem (the dev default; unchanged behavior).
  - `S3Storage(client, bucket)` — S3-compatible via **boto3** (B2). The boto3 client is built
    in an isolated `make_s3_client()` / `_get_s3_client()` from the `S3_*` settings, so tests
    can mock it.
  - `get_storage()` returns the backend per `settings.STORAGE_BACKEND`.
- **`config.py`** — added `STORAGE_BACKEND` (default `local`), `S3_ENDPOINT_URL`, `S3_REGION`,
  `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET`, plus a validator that **fails fast**
  if `STORAGE_BACKEND=s3` without the required S3 vars. `local` stays the default → `docker
  compose up` works with **no B2 credentials**.
- **`attachments.py`** — upload streams the validated bytes to `get_storage().save(...)`;
  download streams them back. Type/size limits and tenant scoping are unchanged.
- **`boto3>=1.34,<2`** added to `backend/pyproject.toml` and `uv.lock` (boto3 1.43.34).

**File-serving choice — proxy through the authenticated endpoint (NOT presigned URLs).**
The download endpoint does `scoped_ticket_or_404(...)` FIRST, then `StreamingResponse`s the
bytes from the storage backend. **Why proxy, not presigned:** the whole guarantee is that a
client can never read another org's attachment, and that check lives in our API. A presigned
URL hands out direct, time-boxed access to the object itself — once minted it bypasses our
scope check, so a leaked/forwarded link (or one issued before a scope changes) could expose a
file cross-org for its TTL. Proxying keeps every byte behind auth + the tenant scope, which is
worth the extra API egress at our file sizes (≤ 50 MB) and scale. (If egress ever matters, the
clean upgrade is short-lived, per-object presigned URLs minted *after* the scope check — but
that weakens the isolation boundary, so we keep proxying for now.)

- **Tests (mock boto3 — no real B2 needed):** `tests/core/test_storage.py` (LocalStorage
  round-trip; `S3Storage` round-trip against a `FakeS3Client`; `get_storage()` selection) and
  `tests/api/routes/test_tickets.py::test_attachment_via_s3_backend` (upload+stream through the
  S3 backend with a mocked client, and **cross-org fetch still → 404**). The fake client lives
  in `tests/utils/fake_s3.py`. All existing attachment + tenant-isolation tests still pass.

### Task 2 — migrations + seed on deploy (Render)  ✅ implemented
Locally, Compose runs migrate+seed via the dedicated `prestart` service. Render runs only the
container's start command, so a fresh Neon DB would never get migrated/seeded. Fix:

- **New `backend/scripts/start.sh`** = `bash scripts/prestart.sh` (wait-for-db →
  `alembic upgrade head` → `initial_data` → idempotent `python -m app.seed`) then
  `exec fastapi run --workers 4 app/main.py`.
- **Render → Settings → Start Command:**

  ```
  bash scripts/start.sh
  ```

  (Working dir is `/app/backend`, matching the Dockerfile.) The seed is idempotent
  (upsert-by-email) so it's safe on **every** deploy. The local Compose flow is untouched —
  the `prestart` service + the override's backend command still handle it; `start.sh` is only
  used where the container itself must migrate/seed.
  Alternative if you're on a plan with a Pre-Deploy Command: set Pre-Deploy =
  `bash scripts/prestart.sh` and leave the default start command.

**Verification:** `make test` → **73 passed** (storage + attachment + all 10 tenant-isolation
cases). Local `STORAGE_BACKEND=local` end-to-end: created a ticket, uploaded a PNG, streamed
it back → HTTP 200, exact bytes, file present on the uploads volume; `docker compose up` still
works with no B2 credentials.

## Seed baseline (Carnera) — demo data removed (2026-06-22)

All placeholder demo data (Pennrose/MQOL/Northwind orgs, their demo users, and every sample
ticket/comment/attachment/activity) was deleted from the seed. The new baseline is one client
org + 12 accounts, no tickets. Idempotent (upsert by email); rerunning never duplicates.
Passwords are shared per family for the internal pilot (`(SEED_CLIENT_PASSWORD in .env)` for clients,
`(SEED_ADMIN_PASSWORD in .env)` for admins), Argon2-hashed, never printed, and overridable via
`SEED_CLIENT_PASSWORD` / `SEED_ADMIN_PASSWORD` env vars. **Rotate + force-change-on-first-login
before any external client access** (deployment task).

```
EMAIL                        FAMILY     ORG        ROLE
------------------------------------------------------------------
bhabani@getcarnera.com       client     Carnera    client_user
sumeet@getcarnera.com        client     Carnera    client_user
piyush@getcarnera.com        client     Carnera    client_user
ankita@getcarnera.com        client     Carnera    client_user
rajesh@getcarnera.com        client     Carnera    client_user
remigius@getcarnera.com      client     Carnera    client_user
bhabani@unveilix.ai          unveilix   —          admin
sumeet@unveilix.ai           unveilix   —          admin
piyush@unveilix.ai           unveilix   —          admin
ankita@unveilix.ai           unveilix   —          admin
rajesh@unveilix.ai           unveilix   —          admin
remigius@unveilix.ai         unveilix   —          admin
```
Verified: fresh DB → `orgs=1 (Carnera, enterprise, active), users=12, tickets=0`; re-running
the seed leaves counts unchanged; both a client (`(SEED_CLIENT_PASSWORD in .env)`) and an admin
(`(SEED_ADMIN_PASSWORD in .env)`) log in (HTTP 200). `make test` → **69 passed** (incl. all 10 tenant-isolation
cases, which build their own two orgs internally).

### Live tenant-isolation verification (new baseline)

A Carnera client created a ticket; an admin onboarded a second org ("Verify Org") and a ticket
there (temporary; removed afterwards to restore the clean baseline):

```
(a) Carnera client sees ONLY Carnera-scoped tickets
   client GET /api/tickets                       -> 1 ticket, orgs=['Carnera']
   client GET /api/tickets/<other-org ticket>    -> HTTP 404   (cannot see another org)
(b) Unveilix admin sees ACROSS orgs
   admin  GET /api/tickets                        -> 2 tickets, orgs=['Carnera','Verify Org']
   admin  GET /api/tickets/<other-org ticket>     -> HTTP 200   (sees every org)
```

## Curl isolation proof

Produced against the seeded data on the live stack (`docker compose up`), using a Pennrose
**client** token (`will.flynn@pennrose.com`) and an Unveilix **team** token
(`adit@unveilix.ai`). `Pennrose ticket` = the client's own org; `MQOL ticket` = another org.

```
Pennrose ticket (client's org): 61824321-8fd0-43f4-9021-af0b1ef0628d
MQOL ticket (another org)     : ee45205e-fe1c-41af-96e5-f6ab50726f2e

=== 1. CLIENT (Pennrose) -> MQOL ticket : expect 404 ===
   client  GET /api/tickets/MQOL      -> HTTP 404
=== 2. CLIENT (Pennrose) -> own ticket  : expect 200 ===
   client  GET /api/tickets/Pennrose  -> HTTP 200
=== 3. TEAM -> ANY org ticket           : expect 200 ===
   team    GET /api/tickets/MQOL      -> HTTP 200
   team    GET /api/tickets/Pennrose  -> HTTP 200
=== 4. CLIENT attach to MQOL ticket     : expect 404 ===
   client  POST .../MQOL/attachments -> HTTP 404

list scoping:
   client GET /api/tickets -> 4 tickets,  orgs=['Pennrose']
   team   GET /api/tickets -> 10 tickets, orgs=['MQOL', 'Northwind Health', 'Pennrose']
```

**Result: a client org can never see/attach-to another org's ticket (404), the Unveilix team
sees every org (200), and within an org every user sees all of that org's tickets.**

UI was also verified end-to-end with a headless Playwright smoke against the Dockerized
frontend (`http://localhost:5174`): client login → Report, only 4 Pennrose tickets,
read-only drawer with no internal comments; team login → Dashboard with a 6-column Kanban,
10 tickets, editable drawer, 3 clients. All assertions passed.

## Test results

`make test` (throwaway Dockerized Postgres, pytest in a fresh container):

```
======================== 67 passed, 1 warning in 10.10s ========================
```

The 10 tenant-isolation acceptance cases (spec §5), all PASSED:

```
test_iso_01_client_list_only_own_org            # client sees only own org's tickets
test_iso_02_client_get_other_org_ticket_404     # cross-org GET -> 404 (not 403)
test_iso_03_client_internal_comment_rejected    # client is_internal=true -> 403
test_iso_04_client_patch_forbidden              # client PATCH -> 403
test_iso_05_internal_comments_hidden_from_client# internal notes absent for client, seen by team
test_iso_06_team_sees_all_orgs                  # agent sees Org A + Org B
test_iso_07_team_org_filter                     # agent ?organization_id=A -> only A
test_iso_08_priority_from_blocks_work           # blocks_work -> P1 (major -> P2)
test_iso_09_unique_reference                    # auto UVX-#### unique reference
test_iso_10_client_attachment_to_other_org_404  # cross-org upload -> 404 (own -> 201)
```

Plus auth (`test_auth_login_returns_token_and_user`, `test_auth_me`,
`test_auth_unauthenticated_401`, `test_wrong_role_team_only_endpoints_403`,
`test_admin_only_create_org_forbidden_for_agent`, `test_auth_login_bad_password`) and the
lifecycle (`test_ticket_lifecycle`: create→assign→in_development→in_testing→deployed→
closed; asserts 6 activity rows incl. 1 created + 1 assigned + 4 status_changed, closed_at
set, priority override logged).
