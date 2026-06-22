"""
Change log:
[#004] 2026-06-22 — Sumeet — Externalised the pilot passwords out of source: the in-file
        defaults are now non-secret placeholders; the real values come from SEED_CLIENT_PASSWORD
        / SEED_ADMIN_PASSWORD (kept in the gitignored .env) so no real password lives in this
        (public) repo.
[#003] 2026-06-22 — Sumeet — Removed ALL demo/dummy data (the Pennrose/MQOL/Northwind orgs,
        their demo users, and every sample ticket/comment/attachment/activity). The new
        baseline seeds exactly one client org (Carnera) with 6 client users and 6 Unveilix
        admin users. Upsert-by-email keeps it idempotent; passwords are Argon2-hashed via the
        app hasher and are NEVER printed. The seed prints a no-secrets account summary table.
[#002] 2026-06-22 — Sumeet — Carry an optional `rca` per ticket and give the seeded closed
        ticket (UVX-1025) a root-cause analysis.
[#001] 2026-06-22 — Sumeet — File created. Idempotent seed (spec §8): 3 orgs, a client user

Run:  python -m app.seed        (inside the backend container; `make seed`)

NOTE: the real pilot passwords are NOT in this file (it is a public repo). Set them via
SEED_CLIENT_PASSWORD / SEED_ADMIN_PASSWORD (e.g. in the gitignored .env); the in-source
defaults below are non-secret placeholders. Rotate + force-change-on-first-login before any
external client uses the system.
"""

import logging
import os

from sqlmodel import Session, select

from app.core.db import engine, init_db
from app.core.security import get_password_hash
from app.models import Family, Organization, Plan, Role, User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

# Pilot passwords come from the environment (kept out of source for a public repo). The
# defaults here are NON-SECRET placeholders — set SEED_CLIENT_PASSWORD / SEED_ADMIN_PASSWORD
# (e.g. in the gitignored .env) for the real values. NEVER logged.
CLIENT_PASSWORD = os.environ.get("SEED_CLIENT_PASSWORD", "changeme-client")
ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "changeme-admin")

CLIENT_ORG_NAME = "Carnera"

# Local-parts; client users are @getcarnera.com, Unveilix admins are @unveilix.ai.
CARNERA_CLIENTS = ["bhabani", "sumeet", "piyush", "ankita", "rajesh", "remigius"]
UNVEILIX_ADMINS = ["bhabani", "sumeet", "piyush", "ankita", "rajesh", "remigius"]


def _display_name(local: str) -> str:
    return local.capitalize()


def goc_org(session: Session, name: str, plan: Plan) -> Organization:
    """Get-or-create an organization by name (idempotent)."""
    org = session.exec(select(Organization).where(Organization.name == name)).first()
    if org:
        if not org.is_active:
            org.is_active = True
            session.add(org)
            session.commit()
        return org
    org = Organization(name=name, plan=plan.value, is_active=True)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


def upsert_user(
    session: Session,
    *,
    email: str,
    full_name: str,
    family: Family,
    role: Role,
    organization_id=None,
    password: str,
) -> User:
    """Idempotent upsert keyed on email. On re-run, fields (including the Argon2-hashed
    password) are refreshed so running the seed repeatedly never creates duplicates."""
    user = session.exec(select(User).where(User.email == email)).first()
    hashed = get_password_hash(password)
    is_superuser = role == Role.admin
    if user:
        user.full_name = full_name
        user.family = family.value
        user.role = role.value
        user.organization_id = organization_id
        user.is_superuser = is_superuser
        user.hashed_password = hashed
        user.is_active = True
    else:
        user = User(
            email=email,
            full_name=full_name,
            family=family.value,
            role=role.value,
            organization_id=organization_id,
            is_superuser=is_superuser,
            hashed_password=hashed,
        )
        session.add(user)
    session.commit()
    session.refresh(user)
    return user


def seed() -> None:
    summary: list[tuple[str, str, str, str]] = []  # (email, family, org, role)
    with Session(engine) as session:
        # Ensure the bootstrap superuser exists (init_db uses FIRST_SUPERUSER from .env).
        init_db(session)

        carnera = goc_org(session, CLIENT_ORG_NAME, Plan.enterprise)

        # 6 Carnera client users.
        for local in CARNERA_CLIENTS:
            email = f"{local}@getcarnera.com"
            upsert_user(
                session,
                email=email,
                full_name=_display_name(local),
                family=Family.client,
                role=Role.client_user,
                organization_id=carnera.id,
                password=CLIENT_PASSWORD,
            )
            summary.append((email, "client", CLIENT_ORG_NAME, "client_user"))

        # 6 Unveilix admin/team users (no organization).
        for local in UNVEILIX_ADMINS:
            email = f"{local}@unveilix.ai"
            upsert_user(
                session,
                email=email,
                full_name=_display_name(local),
                family=Family.unveilix,
                role=Role.admin,
                organization_id=None,
                password=ADMIN_PASSWORD,
            )
            summary.append((email, "unveilix", "—", "admin"))

    _print_summary(summary)


def _print_summary(rows: list[tuple[str, str, str, str]]) -> None:
    """Print an account summary table — emails/family/org/role only, never passwords."""
    line = "=" * 78
    logger.info("\n%s\nSEEDED ACCOUNTS (passwords NOT shown)\n%s", line, line)
    logger.info("%-28s %-10s %-10s %-12s", "EMAIL", "FAMILY", "ORG", "ROLE")
    logger.info("%s", "-" * 78)
    for email, family, org, role in rows:
        logger.info("%-28s %-10s %-10s %-12s", email, family, org, role)
    logger.info("%s", line)
    logger.info(
        "%d accounts seeded (%d Carnera clients, %d Unveilix admins). "
        "Passwords are set via the seed (Argon2-hashed) and shared per family; rotate before "
        "any external client access.",
        len(rows),
        sum(1 for r in rows if r[1] == "client"),
        sum(1 for r in rows if r[1] == "unveilix"),
    )


if __name__ == "__main__":
    logger.info("Seeding Unveilix Support baseline (Carnera org + accounts)…")
    seed()
    logger.info("Seed complete.")
