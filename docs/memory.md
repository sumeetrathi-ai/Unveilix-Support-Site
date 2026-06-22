<!--
  memory.md — RESUME JOURNAL for the Unveilix Support build.
  Purpose: if the session dies / loses context, READ THIS FILE FIRST, then continue
  from "NEXT STEP". Updated after every meaningful step. Newest status at top.
  Companion files: ../PROGRESS.md (phase checklist + curl proof deliverable),
  ../docs/BUILD_PROMPT.md (instructions), ../docs/UNVEILIX_SUPPORT_SPEC.md (spec),
  ../docs/unveilix-support.html (UI target).
-->

# Unveilix Support — Build Resume Journal

> **How to resume:** read this whole file, then do the **NEXT STEP** at the bottom of
> the "Current status" block. Verify the last "DONE" item actually holds (run the
> check noted next to it) before trusting it.

## Project layout (decided)
- Repo root = `/home/sumeetub/projects/Unveilix-Support-App` (scaffold lives flat here).
- Original input docs preserved in `docs/` (BUILD_PROMPT.md, UNVEILIX_SUPPORT_SPEC.md,
  unveilix-support.html, README.md = original build-package readme).
- `.copier-venv/` = isolated venv holding `copier` (build tool only; gitignore it).
- Scaffolded from **official `fastapi/full-stack-fastapi-template`** (copier, vcs HEAD).
- copier created a `.git` repo (branch `master`, base commit `248d7d1`).

## Key facts about the template (so I don't re-learn them)
- Backend is a **uv workspace**: root `pyproject.toml` + `uv.lock` define workspace;
  `backend/pyproject.toml` = package `app`. Backend image built via `uv sync` (Dockerfile).
- ORM = **SQLModel**. All models in single file `backend/app/models.py` (User + Item example).
- API prefix = **`/api/v1`** in template; **spec wants `/api`** → must change
  `API_V1_STR` in `backend/app/core/config.py` to `/api` in Phase 2.
- Auth: JWT via `pyjwt`; `backend/app/api/deps.py` has get_current_user / CurrentUser /
  get_current_active_superuser; login at `/login/access-token` (OAuth2 password form).
- `backend/app/core/db.py::init_db` creates FIRST_SUPERUSER from .env. Migrations run via
  Alembic in `backend/scripts/prestart.sh` (prestart compose service).
- `backend/app/crud.py` has create_user etc. Routes in `backend/app/api/routes/`
  (items, login, users, utils, private). `api/main.py` wires routers.
- Health check endpoint: `GET /api/v1/utils/health-check/` (used by backend healthcheck).
- Compose: `compose.yml` (prod/Traefik) + `compose.override.yml` (local dev: exposes
  backend :8000, frontend :5173, db :5432, adminer :8080, mailcatcher, proxy :80/:8090,
  playwright). db image = `postgres:18`. Named volume `app-db-data`.
- `.env` at repo root holds real dev secrets (generated, gitignored). Non-secret:
  PROJECT_NAME='Unveilix Support', STACK_NAME=unveilix-support, FIRST_SUPERUSER=
  sumeet@unveilix.ai, POSTGRES_DB=app, POSTGRES_USER=postgres, DOMAIN=localhost.
- Frontend: Vite + React + TS in `frontend/`, TanStack Query/Router, generated client,
  Chakra UI. bun.lock present. Dockerfile builds prod nginx image.

## Decisions log (also mirrored in PROGRESS.md)
- D1: Chose official template (current, exact stack). Buuntu only if blocker. No blocker hit.
- D2: Installed `copier` in isolated `.copier-venv` (build tool; explicitly required by prompt).
- D3: Moved 3 input docs + original README into `docs/` to scaffold flat at root.
- D4: Will run tests INSIDE the backend container (template's pytest harness) — avoids
  needing local `uv`. `make test` will wrap this.
- D5 (pending Phase 2): change API prefix `/api/v1` → `/api` per spec §4.

## Change-tracking convention (user's global CLAUDE.md)
- New files I author: add a change-log header block `[#001] YYYY-MM-DD — Sumeet — File created`.
- Files I MODIFY from the template: full attribution block (Before/After/Why + commented
  old code) + header entry. Applied to domain-meaningful files. Today's date: 2026-06-22.

---

## CURRENT STATUS

### DONE
- [x] Read BUILD_PROMPT.md, UNVEILIX_SUPPORT_SPEC.md, unveilix-support.html.
      (check: files in `docs/`)
- [x] Verified env: Docker 29.1.3 + Compose v5.0.1 (daemon up), Python 3.12, Node 22,
      git 2.43, GitHub reachable, 931G free. copier/uv/pipx were absent.
      (check: `docker info`, `node -v`)
- [x] Installed copier 9.15.2 in `.copier-venv`. (check: `.copier-venv/bin/copier --version`)
- [x] Scaffolded official template into repo root via copier (exit 0).
      (check: `ls backend frontend compose.yml`)
- [x] Studied template: compose files, backend Dockerfile, models.py, deps.py,
      config.py, db.py.

### PORT MAP (IMPORTANT — host already runs the real Unveilix dev stack)
The host runs unveilix-postgres:5432, unveilix-home:5173, unveilix-api-server:8080, etc.
My app uses SHIFTED host ports (edited compose.override.yml [#001], gated extras behind
Compose profiles "tools"/"test"):
- backend  : http://localhost:8000   (free)
- db       : localhost:5433 -> 5432
- frontend : http://localhost:5174 -> 80
- adminer  : localhost:8081 (profile "tools")
Bare `docker compose up` now starts only db+prestart+backend+frontend.

### DONE (Phase 0 baseline CONFIRMED)
- [x] compose.override.yml port remap + profiles ([#001]). down/up clean.
- [x] Baseline up: db healthy, prestart exit 0 (migrations + superuser), backend healthy.
- [x] PROVEN via curl: GET /api/v1/utils/health-check/ -> 200 true; POST
      /api/v1/login/access-token (sumeet@unveilix.ai / (FIRST_SUPERUSER_PASSWORD in .env)) -> JWT;
      GET /api/v1/users/me -> 200. Template superuser id e52d3295-...
- [ ] frontend baseline: bg task `bj9cba57m` building+serving at :5174 (in progress).

### PHASE 1 — DONE & VERIFIED (2026-06-22)
- models.py rewritten: Organization, User(extended), Ticket, Attachment, Comment, Activity
  + all Create/Update/Public schemas + enums + SEVERITY_TO_PRIORITY. Enums stored as TEXT.
- Removed items example: deleted routes/items.py, tests/api/routes/test_items.py; fixed
  crud.py, api/main.py, api/routes/users.py (delete), api/routes/private.py, core/db.py.
- Squashed 5 template migrations -> 1 initial migration
  `backend/app/alembic/versions/b8691bbba9a0_unveilix_support_initial_schema.py`
  (revision b8691bbba9a0, down_revision None). size_bytes = BigInteger (model+migration).
- VERIFIED: 6 tables created; CHECK `ck_user_family_organization` present AND enforced
  (psql rejected client-without-org and unveilix-with-org); seeded admin valid
  (unveilix/admin, is_superuser=t, org NULL); login + /me OK with new code.
- HOW MIGRATIONS RUN: prestart service runs `alembic upgrade head` + initial_data.py.
  To regenerate: wipe db (`docker compose down -v`), up db, then
  `docker compose run --rm --no-deps -v "$PWD/backend/app/alembic/versions:/app/backend/app/alembic/versions" backend alembic revision --autogenerate -m "..."`,
  then REBUILD backend image to bake the new migration file before `up`.

### PHASE 2 — DONE & VERIFIED (2026-06-22)
- config.py: API_V1_STR="/api"; added UPLOADS_DIR/MAX_UPLOAD_BYTES/ALLOWED_UPLOAD_TYPES.
- compose.yml: backend healthcheck -> /api/utils/health-check/; added app-uploads volume.
- deps.py: get_current_team_user, get_current_admin, get_ticket_scope (THE scope),
  scoped_ticket_or_404. TeamUser/AdminUser/TicketScope annotated deps.
- crud.py: next_ticket_reference, priority_for_severity, record_activity, create_ticket,
  build_ticket_summaries + name/count map helpers (no N+1).
- routes: auth.py (/auth/login JSON, /auth/me), tickets.py (list/board/{id}/POST/PATCH/
  comments — board declared BEFORE /{id}), attachments.py (POST /tickets/{id}/attachments,
  GET /attachments/{id}), organizations.py, dashboard.py. Wired in api/main.py.
- Import smoke OK (35 routes). Health 200 on /api; /api/v1 now 404.
- CURL SMOKE (/tmp/smoke.sh): PASS=20 FAIL=0 covering isolation #1-#7 + #10, internal-
  comment hiding (client hidden / team visible), role 403s (PATCH, dashboard, board,
  internal comment), priority P1 from blocks_work, UVX-#### ref, attachment scope (404 vs
  201), assign+close lifecycle (closed_at set, 3 activity rows).
- NOTE: smoke created data in the DEV db (Pennrose/MQOL + users + a few tickets). Phase 4
  seed must wipe/own the DB; for final proof do `docker compose down -v` then seed.
- DEV admin creds: sumeet@unveilix.ai / (FIRST_SUPERUSER_PASSWORD in .env) (from .env FIRST_SUPERUSER).
- POST /api/users/ requires TRAILING SLASH (template route).

### PHASE 3 — DONE & VERIFIED (2026-06-22): `make test` -> 67 passed
- Adapted template tests: UserCreate default -> family=unveilix/role=agent; full_name made
  OPTIONAL in schema (UserBase) but NOT NULL on User table (override) + derived in
  crud.create_user; sed-added full_name to bare UserCreate(...) calls; fixed 3 direct
  User(...) constructions (test_login bcrypt x2, crud/test_user bcrypt x1) to pass
  full_name+family=unveilix; conftest cleanup rewritten (no Item; FK-safe delete; keeps
  superuser); deleted tests/utils/item.py; restored `col` import in users.py.
- NEW tests/api/routes/test_tickets.py: 10 isolation cases + auth + lifecycle + extras (18).
- Dockerfile now COPYs ./backend/tests so tests run baked (no bind mount).
- Makefile created: make up/down/fresh/logs/seed/test/test-isolation. `make test` =
  build -> down -v -> up db prestart -> run pytest in fresh container -> down -v.
- BIG LESSON (cost me lots of cycles): the superuser-login test failures were NOT a product
  bug — real curl login works (200). They were caused by (a) a CORRUPTED superuser row left
  in the shared dev DB by my repeated manual delete/recreate diagnostics (conftest.init_db
  only creates-if-missing, never repairs), and (b) stale host __pycache__ when bind-mounting
  app/. FIX/RULE: ALWAYS run tests on a CLEAN cycle (down -v; up db prestart) and run tests
  with app/ BAKED (rebuild image) — `make test` does exactly this. Don't bind-mount app/.

### PHASE 4 — DONE & VERIFIED (2026-06-22)
- backend/app/seed.py: idempotent (get-or-create by org name / email / ticket reference).
  3 orgs, 1 client each, team users sumeet(admin, from FIRST_SUPERUSER)+adit/anubhav/nick
  (agents), 10 mockup tickets UVX-1042..1022 (all 6 statuses) + activity + 2 comments +
  placeholder attachment files (1x1 PNG / webm stub) so UI is alive.
- Wired into backend/scripts/prestart.sh (runs after initial_data) -> `docker compose up`
  auto-seeds. Also `make seed` (= docker compose exec backend python -m app.seed).
- IMPORTANT FIX: added app-uploads volume mount to the PRESTART service in compose.yml too
  (not just backend), else seed-written attachment files land in prestart's ephemeral FS and
  GET /attachments 404s. Verified attachment stream 200 (own) / 404 (cross-org).
- Verified idempotent (counts stable: orgs=3 users=7 tickets=10 activity=24 attachments=7
  comments=2). Client login scoped to own org (will.flynn -> 4 Pennrose tickets); team adit
  -> all 10 across 3 orgs.
- SEEDED CREDENTIALS: admin sumeet@unveilix.ai / (FIRST_SUPERUSER_PASSWORD in .env) ;
  agents adit@/anubhav@/nick@unveilix.ai / (former demo password, removed) ;
  clients will.flynn@pennrose.com, ops@mqol.com, it@northwind.health / (former demo password, removed).

### PHASE 5 — DONE & VERIFIED (2026-06-22)
- Frontend rebuilt as Vite+React+TS, plain CSS (mockup ported to src/index.css), tiny
  built-in router (src/router.tsx), hand fetch client (src/api.ts), TanStack Query kept.
  Dropped TanStack Router/Tailwind/shadcn/generated-client; build script = `vite build`.
- Files: src/{main,App,api,auth,router,toast,types,ui}.tsx + components/{Sidebar,TicketDrawer,
  ScreenRecorder,Kanban}.tsx + pages/{Login,Report,MyTickets,Dashboard,Board,AllTickets,
  Clients}.tsx. index.html title + Inter/JetBrains fonts.
- Backend addition: GET /api/users/team (team-only) for assignee dropdown (users.py).
- CORS: added http://localhost:5174 (docker) + :5180 (vite dev) to BACKEND_CORS_ORIGINS in
  .env (frontend/.env sets VITE_API_URL=http://localhost:8000, so SPA calls backend absolute).
- Created ROOT .dockerignore (build context is repo root; frontend/.dockerignore doesn't
  apply) excluding node_modules/venvs/etc.
- VERIFIED: `npm run build` ok; frontend Docker image builds; headless Playwright smoke
  (frontend/ui_smoke.mjs vs vite dev :5180) PASS — client: 4 Pennrose rows, drawer read-only
  (no status select), no internal comments; team: dashboard 6 kanban cols, 10 list rows,
  drawer editable (status select), 3 clients. Screenshots in /tmp/uishots confirm dark-navy
  theme matches mockup (dashboard, report, drawer with video player + diagnostics).
- Dev workflow: `cd frontend && npm install && npm run dev` (vite :5180, proxies /api).
  Playwright chromium installed at ~/.cache/ms-playwright (headless shell).

### PHASE 6 — DONE & VERIFIED (2026-06-22) — BUILD COMPLETE
- Fixed prestart/backend parallel-build race: removed prestart's duplicate `build:` in
  compose.yml (prestart reuses backend:latest). `docker compose up --build` now works as ONE
  command from a clean `down -v`: db+prestart(migrate+seed)+backend+frontend all healthy.
- Ports live: web http://localhost:5174, api http://localhost:8000 (/docs), db :5433.
- CURL ISOLATION PROOF captured + pasted in PROGRESS.md: client->other org 404, client->own
  200, team->any 200, client cross-org attach 404; list scoping client=4 Pennrose, team=10/3 orgs.
- UI smoke vs DOCKERIZED frontend :5174 (BASE=... node frontend/ui_smoke.mjs) PASS.
- Final `make test` -> 67 passed.
- README.md rewritten (prereqs, one-command up, ports, seeded creds table, make test,
  architecture, API table, deviations). .env.example created (placeholders). .env +
  .copier-venv + ui_smoke.mjs added to .gitignore. Root .dockerignore created.
- ALL self-verification checklist items TRUE (see PROGRESS.md).
- Caveat noted honestly: live getDisplayMedia screen capture can't be driven headlessly;
  it's implemented + works in a secure context (localhost); seeded recording plays in drawer.

### SEED BASELINE CHANGE (2026-06-22) — demo data removed; Carnera + Unveilix accounts
- seed.py [#003] REWRITTEN: removed ALL demo data (Pennrose/MQOL/Northwind orgs, will.flynn/
  ops/it + adit/anubhav/nick users, and every sample ticket/comment/attachment/activity).
  New baseline: one org **Carnera** (enterprise, active) + 6 client users @getcarnera.com
  (client_user, pw (SEED_CLIENT_PASSWORD in .env)) + 6 admins @unveilix.ai (admin, pw (SEED_ADMIN_PASSWORD in .env)). NO
  tickets seeded. Upsert-by-email (idempotent). Passwords Argon2-hashed, NEVER printed;
  prints a no-secrets summary table. Overridable via SEED_CLIENT_PASSWORD/SEED_ADMIN_PASSWORD.
- IMPORTANT: sumeet@unveilix.ai is BOTH FIRST_SUPERUSER and a seeded admin -> set .env
  FIRST_SUPERUSER_PASSWORD=(SEED_ADMIN_PASSWORD in .env) so init_db + conftest superuser login agree with the
  seed. (If you change the admin seed pw, change FIRST_SUPERUSER_PASSWORD too.)
- Tests already self-contained (build their own 2 orgs); no test referenced demo data. The
  6 names are bhabani/sumeet/piyush/ankita/rajesh/remigius.
- VERIFIED: fresh DB orgs=1/users=12/tickets=0; idempotent re-run unchanged; client+admin
  login 200; `make test` -> 69 passed; live isolation: Carnera client -> only Carnera (404 on
  other org), admin -> across orgs (200). Final state reset to clean Carnera baseline (0 tickets).
- README + PROGRESS.md updated (creds table + seed baseline + verification). .env.example
  documents SEED_* overrides.
- Pilot creds are shared per family — ROTATE + force-change-on-first-login before external use
  (deployment task, next up).

### POST-BUILD FEATURE (2026-06-22) — RCA required to close a bug
- NEW: closing a ticket requires a root-cause analysis. Backend: tickets table `rca` text
  column (additive migration 9f3c1a7be2d0, down_revision b8691bbba9a0); PATCH enforces
  status->closed needs rca (422 otherwise), rca settable via PATCH, returned in TicketDetail
  (models.py, tickets.py [#003]). Seed UVX-1025 gets an rca (seed.py [#002]).
- Frontend (TicketDrawer [#002]): selecting "Closed" reveals an amber required-RCA panel
  (textarea + Cancel/Close ticket; Close disabled until non-empty). Closed tickets show a
  "Root cause analysis" section — editable for team (Save RCA), read-only for clients.
  types.ts + index.css [#004] (.rca-required).
- DECISION (updated per user): RCA is INTERNAL-ONLY — team only. build_ticket_detail returns
  rca=None for client-family (like internal comments); drawer RCA section gated to isTeam +
  labeled "Internal". Test asserts client GET closed ticket -> rca None.
- VERIFIED: backend curl (close w/o rca 422, with rca 200+stored); UI flow (panel appears,
  button disabled empty, close sets status+RCA section, client read-only no status select);
  migration applied to live DB (data preserved); `make test` -> 69 passed (added
  test_close_requires_rca; updated test_ticket_lifecycle to send rca on close).
- NOTE: make test reset the local DB to the clean 10-ticket seed (cleared accumulated test
  tickets). UVX-1025 now the only closed ticket and carries the seeded RCA.

### POST-BUILD ENHANCEMENTS (2026-06-22, user-requested)
- Attachment remove: × button on each report-flow thumbnail (recording + screenshots);
  ScreenRecorder now takes controlled `hasClip` prop. (ScreenRecorder.tsx, Report.tsx, index.css)
- Board fits all 6 columns (no scrollbar): `.board` grid-template-columns -> repeat(6,minmax(0,1fr)).
- Reporter ("Raised by") + reported date shown on Kanban cards (.card-sub), AllTickets table
  (new "Raised by" + "Reported" columns), MyTickets rows (.row-sub). Helpers formatDate +
  DateFilter component + DATE_PRESETS/sinceIso in ui.tsx.
- "Filter by date" dropdown (Any time / last 24h / 7d / 30d / 90d) on Dashboard, Board,
  AllTickets, MyTickets. Backend: tickets.py [#002] added `created_after: datetime|None` query
  param to list + board endpoints (via _apply_filters). Verified: last 2d=5, 30d=14, all=14.
  NOTE: frontend sends toISOString() (Z format) so no URL `+` issue; if hand-curling, urlencode.
- Verified via headless browser: board 6 cols + overflow 0, card-sub "Raised by Will Flynn ·
  Jun 22, 2026", list columns [ID,Summary,Client,Raised by,Priority,Status,Assignee,Reported],
  Reported filter present, attachment remove 1->0.
- Suite should still be 68 (created_after is additive/optional); not re-run to avoid tearing
  down the user's live session — run `make test` to confirm.

### POST-BUILD FIX (2026-06-22) — screen-recording upload 422
- BUG: submitting a ticket with a screen recording -> "Unsupported file type
  'video/webm;codecs=vp9'". Cause: MediaRecorder's Blob MIME includes the codec param;
  attachments.py exact-matched against ALLOWED_UPLOAD_TYPES (base types only).
- FIX: backend/app/api/routes/attachments.py [#002] — strip media-type params
  (`raw.split(";")[0]`) before validate + kind lookup + store base type. Rebuilt+restarted
  backend (JWT stays valid; no re-login). Verified via live HTTP: video/webm;codecs=vp9 -> 201
  kind=recording, ;codecs=vp8 -> 201, application/pdf -> 422.
- Added regression test test_attachment_accepts_codec_mime in test_tickets.py (suite -> 68;
  not run yet to avoid tearing down the user's live session — run `make test` to confirm).

### (history) NEXT — PHASE 6 (compose & e2e)
Plan: bring up FULL stack via `docker compose up -d` (db+prestart+backend+frontend); confirm
all healthy; frontend serves at :5174; run a UI smoke vs :5174 (CORS ready). Produce the
CURL ISOLATION PROOF (client token -> other org ticket = 404; team token -> 200) and paste
into PROGRESS.md. Write root README.md (prereqs, `docker compose up`, ports, seeded creds,
`make test`, architecture note, deviations). Final self-verification checklist pass.
Remember ports: web :5174, api :8000, db :5433. Seeded creds in PHASE 4 notes.

### (history) NEXT — PHASE 5 (React frontend)
Port unveilix-support.html to React (Vite+TS, in frontend/). Match dark-navy tokens (§9).
Stack already has TanStack Query/Router + generated client + Chakra. DECISION: build with
plain CSS (CSS variables from the mockup) for faithful theme, keep TanStack Query/Router;
write a small typed API client (fetch) hitting /api. Routes: /login; client /report (+ screen
recording via getDisplayMedia+MediaRecorder, screenshot upload, severity picker, auto env),
/tickets, /tickets/:id; team /dashboard (KPIs), /board (6-col kanban), /tickets (filter +
org filter), /tickets/:id (editable status/assignee + internal notes), /clients. Redirect by
family after login (client->/report, unveilix->/dashboard). No role chooser. Frontend served
at http://localhost:5174. VITE_API_URL=http://localhost:8000 (dev build arg).
NOTE: frontend Dockerfile builds prod nginx image; for dev iteration may run vite locally or
rebuild image. Check frontend/ structure first (src/, routes, generated client, theme).

### (history) NEXT — PHASE 4 (seed) — see plan
Plan: write backend/app/seed.py (run via `python -m app.seed`), idempotent. Create 3 orgs
(Pennrose[enterprise], MQOL[growth], Northwind Health[enterprise]); a client user per org
(will.flynn@pennrose.com etc.); 2 unveilix users (sumeet@unveilix.ai admin EXISTS via
FIRST_SUPERUSER, adit@unveilix.ai agent); ~10 tickets across orgs/statuses mirroring the
mockup (UVX-1022..1042). Idempotent = get-or-create by natural key (org name, email,
ticket reference). Print seeded credentials at end. Wire into prestart.sh so `docker
compose up` seeds automatically (after initial_data). Document a shared dev password.
Then `make seed` / re-run safe.

### (history) PHASE 3 (pytest acceptance gate)
Plan: read tests/conftest.py + scripts/test.sh; adapt fixtures (orgs, client/team users,
tickets); write tests/api/routes/test_tickets.py with the 10 isolation cases + auth tests
(login, /me, wrong-role 403) + happy-path lifecycle (create->assign->status walk->close,
assert activity rows). Fix existing tests broken by model changes (crud/test_user,
api/routes/test_users — UserCreate now needs family/role/org; UserPublic adds fields).
Run inside container; ALL must pass; paste summary into PROGRESS.md.

### (history) NEXT STEP — PHASE 2 (Backend API) — see plan below

### PHASE 2 PLAN
A. config.py: API_V1_STR "/api/v1" -> "/api" (spec §4). Add UPLOADS_DIR (/app/uploads),
   MAX_UPLOAD_BYTES (50MB), ALLOWED_UPLOAD_TYPES (image/png,image/jpeg,video/webm,video/mp4).
B. compose.yml: backend healthcheck path -> /api/utils/health-check/; add app-uploads
   named volume mounted at /app/uploads on backend (and prestart).
C. deps.py: add get_current_team_user (family==unveilix else 403), get_current_admin
   (role==admin else 403), get_ticket_scope(current_user)->SA condition
   (client: Ticket.organization_id==user.org; unveilix: sa.true()), and helper
   scoped_ticket_or_404(session,user,ticket_id) -> 404 if out of tenant.
D. crud.py: next_ticket_reference(session) (max UVX-#### +1, base 1001), create_ticket(...),
   record_activity(...), summary/detail builders (batch counts + name maps, no N+1).
E. routes: auth.py (POST /auth/login JSON -> {access_token,token_type,user}; GET /auth/me),
   tickets.py (GET /tickets list+filters scoped; GET /tickets/board team; GET /tickets/{id}
   detail scoped 404, internal comments only unveilix; POST /tickets; PATCH /tickets/{id}
   team-only; POST /tickets/{id}/comments — client is_internal=true -> 403),
   attachments.py (POST /tickets/{id}/attachments multipart scoped + limits;
   GET /attachments/{id} stream scoped), organizations.py (GET team w/ counts; POST admin),
   dashboard.py (GET /dashboard/stats team). Reuse users.POST (admin) for user creation.
F. api/main.py: include auth, tickets, attachments, organizations, dashboard.
G. Rebuild + curl-test every endpoint incl. tenant isolation spot-checks.
DECISION: client posting is_internal=true -> 403 (role violation, §4 contract). Spec test #3
   allows "forced to false or 422"; 403 is the stricter, cleaner choice — note in tests.

### (history) Begin **Phase 1 — Database & models**:
   a. Rewrite `backend/app/models.py`: extend User (organization_id nullable FK, family,
      role, full_name REQUIRED, keep is_active; drop is_superuser-driven logic but can map
      admin=superuser). Add Organization, Ticket, Attachment, Comment, Activity SQLModels.
      Enums as `(str, Enum)`: Module, Severity, Priority, Status, Plan, Family, Role.
      UUID PKs, created_at/updated_at (TIMESTAMPTZ default now). DB CheckConstraint:
      family=client => organization_id NOT NULL; family=unveilix => NULL.
   b. Remove the `Item` example: model classes, `api/routes/items.py`, its include in
      `api/main.py`, and `crud` item refs. Update `crud.create_user` for new fields.
   c. Fix `core/db.py::init_db` / `initial_data.py` so the FIRST_SUPERUSER is created with
      family=unveilix, role=admin (valid under the constraint).
   d. Generate Alembic migration (autogenerate) INSIDE the backend container against db.
      Note: source isn't bind-mounted in `up -d` (only `docker compose watch` syncs), so
      REBUILD backend image after editing, OR run alembic via `docker compose run --rm`
      with the rebuilt image. Plan: edit files -> `docker compose build backend` ->
      `docker compose run --rm backend alembic revision --autogenerate -m "unveilix domain"`
      -> review migration -> `alembic upgrade head`.
3. Then Phases 2-6 per PROGRESS.md.

NOTE: editing backend/app/* does NOT hot-affect the running container under `up -d`
(no source bind mount); rebuild image to apply. db data persists in volume app-db-data.

### GOTCHAS / TODO
- Remove `Item`/items example everywhere (model, crud, routes/items.py, api/main.py,
  frontend) once tickets work — see BUILD_PROMPT Phase 0.
- Enforce: client family ⇒ organization_id NOT NULL; unveilix family ⇒ NULL (DB constraint).
- Tenant scope dependency `get_ticket_scope` is THE critical code — every ticket read uses it.
- Internal comments NEVER serialized to client-family responses.
- Out-of-tenant ticket fetch ⇒ 404 (not 403) to avoid leaking existence.
