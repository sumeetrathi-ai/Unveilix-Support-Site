"""
Change log:
[#003] 2026-06-22 — Sumeet — A root-cause analysis (rca) is now REQUIRED to close a ticket
        (422 otherwise); rca is settable via PATCH and returned in the ticket detail.
        Internal-only: rca is never serialized to client-family callers (same as internal
        comments).
[#002] 2026-06-22 — Sumeet — Added a `created_after` date filter to the list + board
        endpoints (powers the "filter by date" dropdowns in the UI).
[#001] 2026-06-22 — Sumeet — File created. Ticket endpoints (spec §4). EVERY read path
        applies the tenant scope (deps.get_ticket_scope / scoped_ticket_or_404): list,
        board, detail, comments. Internal comments are filtered out for client-family
        callers. Out-of-tenant access returns 404, never another org's data.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, func, select

from app import crud
from app.api.deps import (
    CurrentUser,
    SessionDep,
    TeamUser,
    get_ticket_scope,
    scoped_ticket_or_404,
)
from app.models import (
    Activity,
    ActivityAction,
    ActivityPublic,
    Attachment,
    AttachmentPublic,
    Comment,
    CommentCreate,
    CommentPublic,
    Family,
    Module,
    Organization,
    Priority,
    Ticket,
    TicketBoard,
    TicketCreate,
    TicketDetail,
    TicketStatus,
    TicketSummary,
    TicketsPublic,
    TicketUpdate,
    User,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def build_ticket_detail(
    *, session: SessionDep, ticket: Ticket, current_user: User
) -> TicketDetail:
    """Assemble the full ticket detail. Internal comments are omitted for clients."""
    is_team = current_user.family == Family.unveilix.value

    org = session.get(Organization, ticket.organization_id)

    # Comments — clients never see internal notes (spec §4 / test #5).
    comment_q = select(Comment).where(Comment.ticket_id == ticket.id)
    if not is_team:
        comment_q = comment_q.where(Comment.is_internal == False)  # noqa: E712
    comments = session.exec(comment_q.order_by(col(Comment.created_at))).all()

    attachments = session.exec(
        select(Attachment)
        .where(Attachment.ticket_id == ticket.id)
        .order_by(col(Attachment.created_at))
    ).all()

    activity = session.exec(
        select(Activity)
        .where(Activity.ticket_id == ticket.id)
        .order_by(col(Activity.created_at))
    ).all()

    # Resolve actor/author/reporter/assignee names in one pass.
    user_ids: set[uuid.UUID] = {ticket.reporter_id}
    if ticket.assignee_id:
        user_ids.add(ticket.assignee_id)
    user_ids |= {c.author_id for c in comments}
    user_ids |= {a.actor_id for a in activity}
    names = crud._name_map(session=session, user_ids=user_ids)

    return TicketDetail(
        id=ticket.id,
        reference=ticket.reference,
        organization_id=ticket.organization_id,
        organization_name=org.name if org else "",
        title=ticket.title,
        description=ticket.description,
        module=ticket.module,  # type: ignore[arg-type]
        severity=ticket.severity,  # type: ignore[arg-type]
        priority=ticket.priority,  # type: ignore[arg-type]
        status=ticket.status,  # type: ignore[arg-type]
        reporter_id=ticket.reporter_id,
        reporter_name=names.get(ticket.reporter_id),
        assignee_id=ticket.assignee_id,
        assignee_name=names.get(ticket.assignee_id) if ticket.assignee_id else None,
        attachment_count=len(attachments),
        comment_count=len(comments),
        environment=ticket.environment,
        # RCA is an internal engineering artifact — never serialized to client-family
        # callers (same rule as internal comments).
        rca=ticket.rca if is_team else None,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        closed_at=ticket.closed_at,
        attachments=[AttachmentPublic.model_validate(a, from_attributes=True) for a in attachments],
        comments=[
            CommentPublic(
                id=c.id,
                ticket_id=c.ticket_id,
                author_id=c.author_id,
                author_name=names.get(c.author_id),
                body=c.body,
                is_internal=c.is_internal,
                created_at=c.created_at,
            )
            for c in comments
        ],
        activity=[
            ActivityPublic(
                id=a.id,
                ticket_id=a.ticket_id,
                actor_id=a.actor_id,
                actor_name=names.get(a.actor_id),
                action=a.action,  # type: ignore[arg-type]
                detail=a.detail,
                created_at=a.created_at,
            )
            for a in activity
        ],
    )


def _apply_filters(
    statement: Any,
    *,
    status: TicketStatus | None,
    priority: Priority | None,
    module: Module | None,
    assignee_id: uuid.UUID | None,
    organization_id: uuid.UUID | None,
    q: str | None,
    created_after: datetime | None,
) -> Any:
    if status is not None:
        statement = statement.where(Ticket.status == status.value)
    if priority is not None:
        statement = statement.where(Ticket.priority == priority.value)
    if module is not None:
        statement = statement.where(Ticket.module == module.value)
    if assignee_id is not None:
        statement = statement.where(Ticket.assignee_id == assignee_id)
    if organization_id is not None:
        # For clients this is redundant with the scope (which already pins their org);
        # for team users it narrows to one org.
        statement = statement.where(Ticket.organization_id == organization_id)
    if created_after is not None:
        # [#002] reported on/after this instant (the UI sends a preset like "last 7 days").
        statement = statement.where(Ticket.created_at >= created_after)
    if q:
        like = f"%{q}%"
        statement = statement.where(
            sa.or_(col(Ticket.title).ilike(like), col(Ticket.reference).ilike(like))
        )
    return statement


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------
@router.get("", response_model=TicketsPublic)
def list_tickets(
    session: SessionDep,
    current_user: CurrentUser,
    status: TicketStatus | None = None,
    priority: Priority | None = None,
    module: Module | None = None,
    assignee_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    q: str | None = None,
    created_after: datetime | None = None,
    skip: int = 0,
    limit: int = Query(default=200, le=500),
) -> Any:
    """List tickets, always tenant-scoped (spec §4 / test #1, #6, #7)."""
    scope = get_ticket_scope(current_user)
    base = _apply_filters(
        select(Ticket).where(scope),
        status=status,
        priority=priority,
        module=module,
        assignee_id=assignee_id,
        organization_id=organization_id,
        q=q,
        created_after=created_after,
    )
    count = session.exec(
        select(func.count()).select_from(base.subquery())
    ).one()
    tickets = session.exec(
        base.order_by(col(Ticket.created_at).desc()).offset(skip).limit(limit)
    ).all()
    return TicketsPublic(
        data=crud.build_ticket_summaries(session=session, tickets=list(tickets)),
        count=count,
    )


# ---------------------------------------------------------------------------
# Board (team only) — MUST be declared before /{ticket_id}
# ---------------------------------------------------------------------------
@router.get("/board", response_model=TicketBoard)
def ticket_board(
    session: SessionDep,
    current_user: TeamUser,
    priority: Priority | None = None,
    module: Module | None = None,
    assignee_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    q: str | None = None,
    created_after: datetime | None = None,
) -> Any:
    """Tickets grouped by status for the six-column Kanban (team only)."""
    scope = get_ticket_scope(current_user)
    base = _apply_filters(
        select(Ticket).where(scope),
        status=None,
        priority=priority,
        module=module,
        assignee_id=assignee_id,
        organization_id=organization_id,
        q=q,
        created_after=created_after,
    )
    tickets = list(
        session.exec(base.order_by(col(Ticket.created_at).desc())).all()
    )
    summaries = crud.build_ticket_summaries(session=session, tickets=tickets)
    columns: dict[str, list[TicketSummary]] = {s.value: [] for s in TicketStatus}
    for summary in summaries:
        columns[summary.status.value].append(summary)
    return TicketBoard(columns=columns)


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------
@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(
    session: SessionDep, current_user: CurrentUser, ticket_id: uuid.UUID
) -> Any:
    """Full ticket detail. 404 if outside the caller's tenant (test #2). Internal
    comments are absent for client callers (test #5)."""
    ticket = scoped_ticket_or_404(
        session=session, current_user=current_user, ticket_id=ticket_id
    )
    return build_ticket_detail(
        session=session, ticket=ticket, current_user=current_user
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
@router.post("", response_model=TicketDetail, status_code=201)
def create_ticket(
    session: SessionDep, current_user: CurrentUser, ticket_in: TicketCreate
) -> Any:
    """Create a ticket. Clients are pinned to their own org; team users must name the
    org. Priority is derived from severity; a UVX-#### reference is generated; a
    `created` activity row is written (spec §4 / tests #8, #9)."""
    if current_user.family == Family.client.value:
        organization_id = current_user.organization_id
    else:
        if ticket_in.organization_id is None:
            raise HTTPException(
                status_code=422,
                detail="organization_id is required when the Unveilix team creates a ticket",
            )
        org = session.get(Organization, ticket_in.organization_id)
        if not org or not org.is_active:
            raise HTTPException(status_code=404, detail="Organization not found")
        organization_id = ticket_in.organization_id

    ticket = crud.create_ticket(
        session=session,
        ticket_in=ticket_in,
        organization_id=organization_id,  # type: ignore[arg-type]
        reporter_id=current_user.id,
    )
    return build_ticket_detail(
        session=session, ticket=ticket, current_user=current_user
    )


# ---------------------------------------------------------------------------
# Update (team only)
# ---------------------------------------------------------------------------
@router.patch("/{ticket_id}", response_model=TicketDetail)
def update_ticket(
    session: SessionDep,
    current_user: TeamUser,
    ticket_id: uuid.UUID,
    ticket_in: TicketUpdate,
) -> Any:
    """Team-only: change status / priority / assignee / rca. Each change writes an activity
    row; status=closed stamps closed_at and REQUIRES a root-cause analysis (spec §4 / test
    #4)."""
    ticket = scoped_ticket_or_404(
        session=session, current_user=current_user, ticket_id=ticket_id
    )
    data = ticket_in.model_dump(exclude_unset=True)

    # Apply RCA first, so a single PATCH {status: closed, rca: "..."} satisfies the
    # close-requires-RCA rule below.
    if "rca" in data:
        ticket.rca = (data["rca"] or "").strip() or None

    if "status" in data and data["status"] is not None:
        new_status = TicketStatus(data["status"]).value
        if new_status != ticket.status:
            # A bug can only be closed with a documented root-cause analysis.
            if new_status == TicketStatus.closed.value and not (
                ticket.rca and ticket.rca.strip()
            ):
                raise HTTPException(
                    status_code=422,
                    detail="A root-cause analysis (rca) is required to close a ticket",
                )
            crud.record_activity(
                session=session,
                ticket_id=ticket.id,
                actor_id=current_user.id,
                action=ActivityAction.status_changed,
                detail={"from": ticket.status, "to": new_status},
                commit=False,
            )
            ticket.status = new_status
            if new_status == TicketStatus.closed.value:
                ticket.closed_at = datetime.now(timezone.utc)
            else:
                ticket.closed_at = None

    if "priority" in data and data["priority"] is not None:
        new_priority = Priority(data["priority"]).value
        if new_priority != ticket.priority:
            crud.record_activity(
                session=session,
                ticket_id=ticket.id,
                actor_id=current_user.id,
                action=ActivityAction.priority_changed,
                detail={"from": ticket.priority, "to": new_priority},
                commit=False,
            )
            ticket.priority = new_priority

    if "assignee_id" in data:
        new_assignee = data["assignee_id"]
        if new_assignee is not None:
            assignee = session.get(User, new_assignee)
            if not assignee or assignee.family != Family.unveilix.value:
                raise HTTPException(
                    status_code=422,
                    detail="Assignee must be an Unveilix-team user",
                )
        if new_assignee != ticket.assignee_id:
            crud.record_activity(
                session=session,
                ticket_id=ticket.id,
                actor_id=current_user.id,
                action=ActivityAction.assigned,
                detail={
                    "from": str(ticket.assignee_id) if ticket.assignee_id else None,
                    "to": str(new_assignee) if new_assignee else None,
                },
                commit=False,
            )
            ticket.assignee_id = new_assignee

    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return build_ticket_detail(
        session=session, ticket=ticket, current_user=current_user
    )


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------
@router.post("/{ticket_id}/comments", response_model=CommentPublic, status_code=201)
def add_comment(
    session: SessionDep,
    current_user: CurrentUser,
    ticket_id: uuid.UUID,
    comment_in: CommentCreate,
) -> Any:
    """Add a comment. Clients may only post public comments — an attempt to post an
    internal note is rejected with 403 (spec §4 / test #3). Scoped: clients can only
    comment on their own org's tickets."""
    ticket = scoped_ticket_or_404(
        session=session, current_user=current_user, ticket_id=ticket_id
    )
    is_team = current_user.family == Family.unveilix.value
    if comment_in.is_internal and not is_team:
        raise HTTPException(
            status_code=403,
            detail="Client users cannot post internal comments",
        )
    comment = Comment(
        ticket_id=ticket.id,
        author_id=current_user.id,
        body=comment_in.body,
        is_internal=comment_in.is_internal and is_team,
    )
    session.add(comment)
    session.flush()
    crud.record_activity(
        session=session,
        ticket_id=ticket.id,
        actor_id=current_user.id,
        action=ActivityAction.commented,
        detail={"is_internal": comment.is_internal},
        commit=False,
    )
    session.commit()
    session.refresh(comment)
    return CommentPublic(
        id=comment.id,
        ticket_id=comment.ticket_id,
        author_id=comment.author_id,
        author_name=current_user.full_name,
        body=comment.body,
        is_internal=comment.is_internal,
        created_at=comment.created_at,
    )
