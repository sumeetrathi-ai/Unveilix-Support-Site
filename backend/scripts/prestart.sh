#! /usr/bin/env bash
#
# Change log:
# [#001] 2026-06-22 — Sumeet — Run the idempotent Unveilix seed after initial data so a
#         single `docker compose up` brings up a fully populated, demo-ready database.

set -e
set -x

# Let the DB start
python app/backend_pre_start.py

# Run migrations
alembic upgrade head

# Create initial data in DB (the FIRST_SUPERUSER admin)
python app/initial_data.py

# [#001] --by Sumeet (2026-06-22)
# Before: prestart ended after initial_data.py (admin only).
# After: also run the idempotent seed (orgs, client/team users, ~10 sample tickets).
# Why: spec §8 wants `docker compose up` to land in a populated state so the UI is alive.
python -m app.seed
