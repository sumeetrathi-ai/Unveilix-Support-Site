"""
Change log:
[#002] 2026-06-22 — Sumeet — Added the ticket domain data layer: reference generation,
        priority-from-severity, ticket creation, activity logging, and batch summary/detail
        builders (org name, reporter/assignee names, attachment/comment counts) that avoid
        N+1 queries.
[#001] 2026-06-22 — Sumeet — Removed the Item example CRUD and made create_user persist
        the new family/role/is_superuser fields as plain text (enum .value) so they land in
        the TEXT columns unambiguously.
"""

import re
import uuid
from typing import Any

from sqlmodel import Session, func, select

from app.core.security import get_password_hash, verify_password
from app.models import (
    SEVERITY_TO_PRIORITY,
    Activity,
    ActivityAction,
    Attachment,
    Comment,
    Organization,
    Severity,
    Ticket,
    TicketCreate,
    TicketSummary,
    User,
    UserCreate,
    UserUpdate,
)
from app.models import Role  # noqa: E402  (kept after the domain imports for clarity)


def create_user(*, session: Session, user_create: UserCreate) -> User:
    # [#001] --by Sumeet (2026-06-22)
    # Before: model_validate only injected hashed_password; family/role didn't exist yet.
    # After: also force family/role/is_superuser into the update dict as plain strings.
    # Why: family/role are TEXT columns validated by Python enums (spec §3); admins are
    #      mapped to is_superuser=True so the template's superuser-gated routes keep working.
    # full_name is optional in the payload but NOT NULL in the DB — derive from the email
    # local-part when the caller didn't supply one.
    full_name = user_create.full_name or user_create.email.split("@")[0]
    db_obj = User.model_validate(
        user_create,
        update={
            "hashed_password": get_password_hash(user_create.password),
            "full_name": full_name,
            "family": user_create.family.value,
            "role": user_create.role.value,
            "is_superuser": user_create.is_superuser
            or user_create.role == Role.admin,
        },
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    # [#001] --by Sumeet (2026-06-22)
    # Why: role is a TEXT column validated by the Role enum; store its string value.
    if "role" in user_data and user_data["role"] is not None:
        user_data["role"] = Role(user_data["role"]).value
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


# Dummy hash to use for timing attack prevention when user is not found
# This is an Argon2 hash of a random password, used to ensure constant-time comparison
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        # Prevent timing attacks by running password verification even when user doesn't exist
        # This ensures the response time is similar whether or not the email exists
        verify_password(password, DUMMY_HASH)
        return None
    verified, updated_password_hash = verify_password(password, db_user.hashed_password)
    if not verified:
        return None
    if updated_password_hash:
        db_user.hashed_password = updated_password_hash
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    return db_user


# ===========================================================================
# [#002] Ticket domain data layer
# ===========================================================================
_REF_RE = re.compile(r"UVX-(\d+)$")


def next_ticket_reference(*, session: Session) -> str:
    """Generate the next sequential ``UVX-####`` reference.

    Computes ``max(existing numeric suffix) + 1`` and starts at 1001 when empty.
    (v1 is single-writer enough for this; high-concurrency sequencing is a TODO —
    spec §10 leaves it out of scope.)
    """
    refs = session.exec(select(Ticket.reference)).all()
    max_n = 1000
    for ref in refs:
        m = _REF_RE.search(ref or "")
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"UVX-{max_n + 1}"


def priority_for_severity(severity: Severity) -> str:
    """Map a client-facing severity to the default engineering priority (spec §3)."""
    return SEVERITY_TO_PRIORITY[severity].value


def record_activity(
    *,
    session: Session,
    ticket_id: uuid.UUID,
    actor_id: uuid.UUID,
    action: ActivityAction,
    detail: dict[str, Any] | None = None,
    commit: bool = True,
) -> Activity:
    """Append an audit-trail row to a ticket's timeline."""
    entry = Activity(
        ticket_id=ticket_id,
        actor_id=actor_id,
        action=action.value,
        detail=detail,
    )
    session.add(entry)
    if commit:
        session.commit()
        session.refresh(entry)
    return entry


def create_ticket(
    *,
    session: Session,
    ticket_in: TicketCreate,
    organization_id: uuid.UUID,
    reporter_id: uuid.UUID,
) -> Ticket:
    """Create a ticket: derive priority from severity, generate the reference, and
    write the initial ``created`` activity row — all in one transaction."""
    ticket = Ticket(
        reference=next_ticket_reference(session=session),
        organization_id=organization_id,
        reporter_id=reporter_id,
        title=ticket_in.title,
        description=ticket_in.description,
        module=ticket_in.module.value,
        severity=ticket_in.severity.value,
        priority=priority_for_severity(ticket_in.severity),
        environment=ticket_in.environment,
    )
    session.add(ticket)
    session.flush()  # assign ticket.id before logging activity
    record_activity(
        session=session,
        ticket_id=ticket.id,
        actor_id=reporter_id,
        action=ActivityAction.created,
        detail={
            "severity": ticket.severity,
            "priority": ticket.priority,
            "reference": ticket.reference,
        },
        commit=False,
    )
    session.commit()
    session.refresh(ticket)
    return ticket


def _name_map(*, session: Session, user_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    user_ids = {uid for uid in user_ids if uid is not None}
    if not user_ids:
        return {}
    rows = session.exec(
        select(User.id, User.full_name).where(User.id.in_(user_ids))  # type: ignore[attr-defined]
    ).all()
    return {uid: name for uid, name in rows}


def _org_name_map(
    *, session: Session, org_ids: set[uuid.UUID]
) -> dict[uuid.UUID, str]:
    org_ids = {oid for oid in org_ids if oid is not None}
    if not org_ids:
        return {}
    rows = session.exec(
        select(Organization.id, Organization.name).where(
            Organization.id.in_(org_ids)  # type: ignore[attr-defined]
        )
    ).all()
    return {oid: name for oid, name in rows}


def _count_map(
    *, session: Session, model: Any, ticket_ids: set[uuid.UUID]
) -> dict[uuid.UUID, int]:
    if not ticket_ids:
        return {}
    rows = session.exec(
        select(model.ticket_id, func.count())
        .where(model.ticket_id.in_(ticket_ids))
        .group_by(model.ticket_id)
    ).all()
    return {tid: cnt for tid, cnt in rows}


def build_ticket_summaries(
    *, session: Session, tickets: list[Ticket]
) -> list[TicketSummary]:
    """Build TicketSummary rows for a list of tickets with a fixed, small number of
    batch queries (org names, user names, attachment/comment counts) — no N+1."""
    if not tickets:
        return []
    ticket_ids = {t.id for t in tickets}
    org_ids = {t.organization_id for t in tickets}
    user_ids: set[uuid.UUID] = set()
    for t in tickets:
        user_ids.add(t.reporter_id)
        if t.assignee_id:
            user_ids.add(t.assignee_id)

    orgs = _org_name_map(session=session, org_ids=org_ids)
    names = _name_map(session=session, user_ids=user_ids)
    att_counts = _count_map(session=session, model=Attachment, ticket_ids=ticket_ids)
    com_counts = _count_map(session=session, model=Comment, ticket_ids=ticket_ids)

    summaries: list[TicketSummary] = []
    for t in tickets:
        summaries.append(
            TicketSummary(
                id=t.id,
                reference=t.reference,
                organization_id=t.organization_id,
                organization_name=orgs.get(t.organization_id, ""),
                title=t.title,
                module=t.module,  # type: ignore[arg-type]
                severity=t.severity,  # type: ignore[arg-type]
                priority=t.priority,  # type: ignore[arg-type]
                status=t.status,  # type: ignore[arg-type]
                reporter_id=t.reporter_id,
                reporter_name=names.get(t.reporter_id),
                assignee_id=t.assignee_id,
                assignee_name=names.get(t.assignee_id) if t.assignee_id else None,
                attachment_count=att_counts.get(t.id, 0),
                comment_count=com_counts.get(t.id, 0),
                created_at=t.created_at,
                updated_at=t.updated_at,
                closed_at=t.closed_at,
            )
        )
    return summaries
