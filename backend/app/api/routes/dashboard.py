"""
Change log:
[#001] 2026-06-22 — Sumeet — File created. Team-only dashboard KPIs (spec §4): open count,
        breaching-SLA count (stub policy), deployed-in-last-7-days, and median resolution
        time. SLA is a stub (P1 open > 24h, P2 open > 72h) per spec; real SLA policy is out
        of scope for v1 (spec §10).
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter
from sqlmodel import col, func, select

from app.api.deps import SessionDep, TeamUser
from app.models import DashboardStats, Priority, Ticket, TicketStatus

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_OPEN_STATUSES = [
    TicketStatus.new.value,
    TicketStatus.deferred.value,
    TicketStatus.in_development.value,
    TicketStatus.in_testing.value,
]


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(session: SessionDep, current_user: TeamUser) -> Any:
    """Compute the four headline KPIs shown on the team dashboard."""
    now = datetime.now(timezone.utc)

    open_count = session.exec(
        select(func.count())
        .select_from(Ticket)
        .where(col(Ticket.status).in_(_OPEN_STATUSES))
    ).one()

    # Stub SLA: open P1 older than 24h, open P2 older than 72h.
    p1_breach = session.exec(
        select(func.count())
        .select_from(Ticket)
        .where(col(Ticket.status).in_(_OPEN_STATUSES))
        .where(Ticket.priority == Priority.P1.value)
        .where(Ticket.created_at < now - timedelta(hours=24))
    ).one()
    p2_breach = session.exec(
        select(func.count())
        .select_from(Ticket)
        .where(col(Ticket.status).in_(_OPEN_STATUSES))
        .where(Ticket.priority == Priority.P2.value)
        .where(Ticket.created_at < now - timedelta(hours=72))
    ).one()
    breaching = (p1_breach or 0) + (p2_breach or 0)

    deployed_last_7d = session.exec(
        select(func.count())
        .select_from(Ticket)
        .where(Ticket.status == TicketStatus.deployed.value)
        .where(Ticket.updated_at >= now - timedelta(days=7))
    ).one()

    # Median resolution time across closed tickets (closed_at - created_at), in days.
    closed = session.exec(
        select(Ticket.created_at, Ticket.closed_at)
        .where(Ticket.status == TicketStatus.closed.value)
        .where(col(Ticket.closed_at).is_not(None))
    ).all()
    median_days: float | None = None
    if closed:
        durations = sorted(
            (closed_at - created_at).total_seconds() / 86400.0
            for created_at, closed_at in closed
        )
        n = len(durations)
        mid = n // 2
        median_days = (
            durations[mid]
            if n % 2 == 1
            else (durations[mid - 1] + durations[mid]) / 2.0
        )
        median_days = round(median_days, 1)

    return DashboardStats(
        open_count=open_count or 0,
        breaching_sla_count=breaching,
        deployed_last_7d=deployed_last_7d or 0,
        median_resolution_days=median_days,
    )
