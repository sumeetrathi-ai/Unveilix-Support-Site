# Change log:
# [#001] 2026-06-22 — Sumeet — File created. Developer entrypoints for the Unveilix Support
#         stack: up / down / logs / seed / test. `make test` runs the full pytest suite in a
#         fresh, throwaway DB inside Docker (it resets the local DB — re-run `make up` after).

COMPOSE := docker compose

.PHONY: help up down logs build seed test test-isolation fresh

help:
	@echo "Unveilix Support — make targets:"
	@echo "  make up     - build & start db + api + web (runs migrations + seed)"
	@echo "  make down   - stop all services (keeps data volume)"
	@echo "  make fresh  - stop and DELETE all data volumes"
	@echo "  make logs   - tail logs"
	@echo "  make seed   - (re)run the idempotent seed script"
	@echo "  make test   - run the full pytest suite in a throwaway DB (resets local DB)"
	@echo "  make test-isolation - run only the 10 tenant-isolation cases"

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d --build db prestart backend frontend
	@echo "API:  http://localhost:8000/docs    Web: http://localhost:5174"

down:
	$(COMPOSE) down

fresh:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f

seed:
	$(COMPOSE) exec backend python -m app.seed

# Full test suite in a throwaway DB. Builds the backend (tests are baked into the image),
# wipes any local data, applies the schema via prestart, runs pytest in a fresh container,
# then tears the throwaway stack down again. NOTE: this resets your local DB volume.
test:
	$(COMPOSE) build backend
	$(COMPOSE) down -v
	$(COMPOSE) up -d --wait db prestart
	@set -e; \
	$(COMPOSE) run --rm --no-deps backend python -m pytest tests/ -p no:cacheprovider -v; \
	status=$$?; \
	$(COMPOSE) down -v; \
	exit $$status

test-isolation:
	$(COMPOSE) build backend
	$(COMPOSE) down -v
	$(COMPOSE) up -d --wait db prestart
	@set -e; \
	$(COMPOSE) run --rm --no-deps backend python -m pytest tests/api/routes/test_tickets.py -p no:cacheprovider -v -k iso_; \
	status=$$?; \
	$(COMPOSE) down -v; \
	exit $$status
