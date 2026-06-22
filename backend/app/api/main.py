"""
Change log:
[#002] 2026-06-22 — Sumeet — Wired in the Unveilix domain routers (auth, organizations,
        tickets, attachments, dashboard).
[#001] 2026-06-22 — Sumeet — Removed the `items` example router (Phase 1).
"""

from fastapi import APIRouter

from app.api.routes import (
    attachments,
    auth,
    dashboard,
    login,
    organizations,
    private,
    tickets,
    users,
    utils,
)
from app.core.config import settings

api_router = APIRouter()
# [#001][#002] --by Sumeet (2026-06-22)
# Before: included login, users, utils, items.
# After: dropped items; added auth, organizations, tickets, attachments, dashboard.
# Why: items was the template example; these are the Unveilix Support domain endpoints.
api_router.include_router(auth.router)
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(organizations.router)
api_router.include_router(tickets.router)
api_router.include_router(attachments.router)
api_router.include_router(dashboard.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
