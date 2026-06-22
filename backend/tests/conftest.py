"""
Change log:
[#001] 2026-06-22 — Sumeet — Removed the Item import; clean up the Unveilix domain tables
        (activity, comments, attachments, tickets, organizations) in FK-safe order, and
        preserve the seeded FIRST_SUPERUSER on teardown so other modules keep a valid admin.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.models import (
    Activity,
    Attachment,
    Comment,
    Organization,
    Ticket,
    User,
)
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        init_db(session)
        yield session
        # [#001] --by Sumeet (2026-06-22)
        # Before: delete(Item); delete(User)
        # After: delete the full ticket graph + orgs + non-superuser users, FK-safe order.
        # Why: Item is gone; tickets/comments/etc. must be cleared before users/orgs, and we
        #      keep the FIRST_SUPERUSER so the shared admin survives teardown.
        for model in (Activity, Comment, Attachment, Ticket):
            session.execute(delete(model))
        session.execute(delete(User).where(User.email != settings.FIRST_SUPERUSER))  # type: ignore[arg-type]
        session.execute(delete(Organization))
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
