#! /usr/bin/env bash
#
# Change log:
# [#001] 2026-06-22 — Sumeet — File created. Container START command for hosts (e.g. Render)
#         where the running container must itself migrate + seed before serving — because
#         there is no separate Compose `prestart` service there. It reuses scripts/prestart.sh
#         (wait-for-db + `alembic upgrade head` + initial data + idempotent seed) and then
#         execs the API server. The local Docker Compose flow is unchanged (it still uses the
#         dedicated `prestart` service + the override's own backend command).
#
# Render → Settings → Start Command:   bash scripts/start.sh

set -e

# Run migrations + create initial data + idempotent seed (safe to run on every deploy).
bash scripts/prestart.sh

# Hand off to the API server (replaces this process).
exec fastapi run --workers 4 app/main.py
