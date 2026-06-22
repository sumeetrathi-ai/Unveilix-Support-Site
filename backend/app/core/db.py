"""
Change log:
[#001] 2026-06-22 — Sumeet — Create the FIRST_SUPERUSER as a valid Unveilix-team user
        (family=unveilix, role=admin, with a full_name) so it satisfies the new
        family/organization CHECK constraint and the required full_name field.
"""

from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import Family, Role, User, UserCreate

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        # [#001] --by Sumeet (2026-06-22)
        # Before: UserCreate(email, password, is_superuser=True)  # no family/role/full_name
        # After: a valid unveilix-family admin with a full_name.
        # Why: required full_name + the family/organization CHECK constraint (unveilix users
        #      have no org). role=admin also maps to is_superuser=True via crud.create_user.
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            full_name="Unveilix Admin",
            family=Family.unveilix,
            role=Role.admin,
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)
