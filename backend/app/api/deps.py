"""
Change log:
[#001] 2026-06-22 — Sumeet — Added the tenant-isolation primitives: get_ticket_scope (the
        DB-query-layer scope applied to every ticket read), scoped_ticket_or_404, and the
        role/family guards get_current_team_user (unveilix-only) and get_current_admin.
"""

import uuid
from collections.abc import Generator
from typing import Annotated, Any

import jwt
import sqlalchemy as sa
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session, select

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import Family, Role, Ticket, TokenPayload, User

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


# ===========================================================================
# Role / family guards
# ===========================================================================
def get_current_team_user(current_user: CurrentUser) -> User:
    """Allow only Unveilix-team (family == 'unveilix') users. Clients get 403."""
    if current_user.family != Family.unveilix.value:
        raise HTTPException(
            status_code=403, detail="This action is restricted to the Unveilix team"
        )
    return current_user


def get_current_admin(current_user: CurrentUser) -> User:
    """Allow only Unveilix admins (role == 'admin'). Everyone else gets 403."""
    if (
        current_user.family != Family.unveilix.value
        or current_user.role != Role.admin.value
    ):
        raise HTTPException(
            status_code=403, detail="This action is restricted to Unveilix admins"
        )
    return current_user


TeamUser = Annotated[User, Depends(get_current_team_user)]
AdminUser = Annotated[User, Depends(get_current_admin)]


# ===========================================================================
# Tenant isolation — THE most important code in the app (spec §4)
# ===========================================================================
def get_ticket_scope(current_user: CurrentUser) -> Any:
    """Return the mandatory tenant filter that MUST be ANDed into every ticket query.

    This is the single chokepoint that enforces strict tenant isolation at the
    DATABASE QUERY LAYER (not just the UI):

      * client-family users  -> pinned to their own organization. They can never
        widen this: even if they pass ``?organization_id=<other>`` it is ANDed with
        this condition, so the result set stays inside their org.
      * unveilix-family users -> unrestricted (``sa.true()``); the optional
        ``?organization_id=`` filter is applied separately in the endpoint.

    Every endpoint that READS tickets (list, board, detail, comments, attachments)
    builds its query as ``select(Ticket).where(scope)...`` using this value, and
    single-ticket lookups go through :func:`scoped_ticket_or_404`. Out-of-tenant
    access therefore returns an empty set / 404 — never another org's data.
    """
    if current_user.family == Family.client.value:
        # A client with a NULL org would match nothing (defensive; the DB CHECK
        # constraint guarantees client users always have an organization_id).
        return Ticket.organization_id == current_user.organization_id
    return sa.true()


# Annotated dependency form so routes can declare `scope: TicketScope`.
TicketScope = Annotated[Any, Depends(get_ticket_scope)]


def scoped_ticket_or_404(
    *, session: Session, current_user: User, ticket_id: uuid.UUID
) -> Ticket:
    """Fetch a single ticket honoring the tenant scope.

    Returns 404 (NOT 403) when the ticket is outside the caller's tenant, so that a
    client cannot even learn that another org's ticket exists (spec §4).
    """
    scope = get_ticket_scope(current_user)
    ticket = session.exec(
        select(Ticket).where(Ticket.id == ticket_id).where(scope)
    ).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket
