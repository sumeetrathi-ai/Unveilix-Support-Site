"""
Change log:
[#001] 2026-06-22 — Sumeet — Give privately-created users a valid family/role so they
        satisfy the new family/organization CHECK constraint (default: unveilix/agent,
        which legitimately has no organization).
"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.core.security import get_password_hash
from app.models import (
    Family,
    Role,
    User,
    UserPublic,
)

router = APIRouter(tags=["private"], prefix="/private")


class PrivateUserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    is_verified: bool = False


@router.post("/users/", response_model=UserPublic)
def create_user(user_in: PrivateUserCreate, session: SessionDep) -> Any:
    """
    Create a new user.
    """

    # [#001] --by Sumeet (2026-06-22)
    # Before: User(email, full_name, hashed_password)  # no family/role
    # After: also set family=unveilix, role=agent.
    # Why: the family/organization CHECK constraint rejects a client-family user without an
    #      organization_id; an unveilix-family user with no org is the valid default here.
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        family=Family.unveilix.value,
        role=Role.agent.value,
    )

    session.add(user)
    session.commit()

    return user
