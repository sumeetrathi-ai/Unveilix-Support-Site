"""
Change log:
[#001] 2026-06-22 — Sumeet — File created. Organizations endpoints (spec §4): GET (team
        only) lists orgs with open/deployed ticket counts + a primary contact; POST (admin
        only) onboards a new org.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select

from app.api.deps import AdminUser, SessionDep, TeamUser
from app.models import (
    Family,
    Organization,
    OrganizationCreate,
    OrganizationPublic,
    OrganizationsPublic,
    OrganizationWithCounts,
    Ticket,
    TicketStatus,
    User,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])

_OPEN_STATUSES = [
    TicketStatus.new.value,
    TicketStatus.deferred.value,
    TicketStatus.in_development.value,
    TicketStatus.in_testing.value,
]


@router.get("", response_model=OrganizationsPublic)
def list_organizations(session: SessionDep, current_user: TeamUser) -> Any:
    """List all organizations with their open and deployed ticket counts (team only)."""
    orgs = session.exec(select(Organization).order_by(col(Organization.name))).all()

    # Batch the counts: open tickets and deployed tickets per org.
    open_rows = session.exec(
        select(Ticket.organization_id, func.count())
        .where(col(Ticket.status).in_(_OPEN_STATUSES))
        .group_by(Ticket.organization_id)
    ).all()
    open_counts = {oid: c for oid, c in open_rows}
    deployed_rows = session.exec(
        select(Ticket.organization_id, func.count())
        .where(Ticket.status == TicketStatus.deployed.value)
        .group_by(Ticket.organization_id)
    ).all()
    deployed_counts = {oid: c for oid, c in deployed_rows}

    # Primary contact: the first client user of the org (by email).
    contact_rows = session.exec(
        select(User.organization_id, func.min(User.email))
        .where(User.family == Family.client.value)
        .group_by(User.organization_id)
    ).all()
    contacts = {oid: email for oid, email in contact_rows}

    data = [
        OrganizationWithCounts(
            id=o.id,
            name=o.name,
            plan=o.plan,  # type: ignore[arg-type]
            is_active=o.is_active,
            created_at=o.created_at,
            open_count=open_counts.get(o.id, 0),
            deployed_count=deployed_counts.get(o.id, 0),
            primary_contact=contacts.get(o.id),
        )
        for o in orgs
    ]
    return OrganizationsPublic(data=data, count=len(data))


@router.post("", response_model=OrganizationPublic, status_code=201)
def create_organization(
    session: SessionDep, current_user: AdminUser, org_in: OrganizationCreate
) -> Any:
    """Onboard a new organization (admin only)."""
    existing = session.exec(
        select(Organization).where(Organization.name == org_in.name)
    ).first()
    if existing:
        raise HTTPException(
            status_code=409, detail="An organization with this name already exists"
        )
    org = Organization(name=org_in.name, plan=org_in.plan.value)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org
