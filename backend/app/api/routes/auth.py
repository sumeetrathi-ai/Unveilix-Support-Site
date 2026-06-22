"""
Change log:
[#001] 2026-06-22 — Sumeet — File created. Spec §4 auth endpoints: POST /auth/login
        (JSON {email,password} -> {access_token, token_type, user}) and GET /auth/me.
        The template's OAuth2 form login at /login/access-token is kept (login.py) for the
        OpenAPI "Authorize" button and tooling.
"""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, HTTPException

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.core import security
from app.core.config import settings
from app.models import LoginRequest, LoginResponse, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(session: SessionDep, credentials: LoginRequest) -> Any:
    """Authenticate with email + password; returns a JWT and the user record."""
    user = crud.authenticate(
        session=session, email=credentials.email, password=credentials.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    token = security.create_access_token(
        user.id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserPublic.model_validate(user, from_attributes=True),
    )


@router.get("/me", response_model=UserPublic)
def read_me(current_user: CurrentUser) -> Any:
    """Return the currently authenticated user."""
    return current_user
