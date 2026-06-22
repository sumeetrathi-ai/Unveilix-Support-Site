"""
Change log:
[#001] 2026-06-22 — Sumeet — Replaced the template's example domain (User + Item) with the
        full Unveilix Support domain: extended User (organization_id, family, role,
        required full_name) and added Organization, Ticket, Attachment, Comment and
        Activity models, plus the request/response schemas and shared enums. The original
        template models (User + Item example) are preserved in git history at the scaffold
        commit (248d7d1); they are not inlined here as commented-out code because this is a
        wholesale domain replacement, not an in-place edit (recorded in PROGRESS.md).
        Enums are stored as TEXT columns and validated in the app layer via Python Enums
        (per spec §3); a CHECK constraint enforces the family/organization rule.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import EmailStr, model_validator
from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel
from typing_extensions import Self


def utcnow() -> datetime:
    """Timezone-aware UTC now; used as the default for every timestamp column."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enums (stored as TEXT in the DB, validated here in the app layer — spec §3)
# ---------------------------------------------------------------------------
class Plan(str, Enum):
    growth = "growth"
    enterprise = "enterprise"


class Family(str, Enum):
    client = "client"
    unveilix = "unveilix"


class Role(str, Enum):
    client_user = "client_user"
    agent = "agent"
    admin = "admin"


class Module(str, Enum):
    conversational_query = "conversational_query"
    charts = "charts"
    datasource = "datasource"
    agent_view = "agent_view"
    rbac = "rbac"
    audit_log = "audit_log"
    other = "other"


class Severity(str, Enum):
    blocks_work = "blocks_work"
    major = "major"
    minor = "minor"
    suggestion = "suggestion"


class Priority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class TicketStatus(str, Enum):
    new = "new"
    deferred = "deferred"
    in_development = "in_development"
    in_testing = "in_testing"
    deployed = "deployed"
    closed = "closed"


class AttachmentKind(str, Enum):
    screenshot = "screenshot"
    recording = "recording"


class ActivityAction(str, Enum):
    created = "created"
    status_changed = "status_changed"
    assigned = "assigned"
    priority_changed = "priority_changed"
    commented = "commented"
    attachment_added = "attachment_added"


# Severity -> default engineering priority (spec §3). Team may override later.
SEVERITY_TO_PRIORITY: dict[Severity, Priority] = {
    Severity.blocks_work: Priority.P1,
    Severity.major: Priority.P2,
    Severity.minor: Priority.P3,
    Severity.suggestion: Priority.P4,
}


# ---------------------------------------------------------------------------
# Reusable timestamp column factories (TIMESTAMPTZ, default now)
# ---------------------------------------------------------------------------
def created_at_field() -> Any:
    return Field(
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),  # type: ignore[arg-type]
        nullable=False,
    )


def updated_at_field() -> Any:
    # default on insert + onupdate on every UPDATE (handled by SQLAlchemy)
    return Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            default=utcnow,
            onupdate=utcnow,
            nullable=False,
        ),
    )


# ===========================================================================
# Organizations
# ===========================================================================
class OrganizationBase(SQLModel):
    name: str = Field(max_length=255)
    plan: Plan = Plan.growth


class Organization(SQLModel, table=True):
    __tablename__ = "organizations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255, unique=True, index=True)
    plan: str = Field(default=Plan.growth.value, max_length=32)
    is_active: bool = Field(default=True)
    created_at: datetime = created_at_field()
    updated_at: datetime | None = updated_at_field()


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationPublic(SQLModel):
    id: uuid.UUID
    name: str
    plan: Plan
    is_active: bool
    created_at: datetime


class OrganizationWithCounts(OrganizationPublic):
    open_count: int = 0
    deployed_count: int = 0
    primary_contact: str | None = None


class OrganizationsPublic(SQLModel):
    data: list[OrganizationWithCounts]
    count: int


# ===========================================================================
# Users (extends the template's User; family/role drive tenant isolation)
# ===========================================================================
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    # Optional at the SCHEMA layer (so create payloads may omit it — crud derives it from
    # the email when missing). The DB COLUMN is NOT NULL (overridden on the User table).
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    is_superuser: bool = False


class User(UserBase, table=True):
    __tablename__ = "users"
    __table_args__ = (
        # spec §3: client-family users MUST have an org; unveilix-family MUST NOT.
        CheckConstraint(
            "(family = 'client' AND organization_id IS NOT NULL) OR "
            "(family = 'unveilix' AND organization_id IS NULL)",
            name="ck_user_family_organization",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # NOT NULL at the DB layer (spec §3) — overrides the optional schema field above.
    full_name: str = Field(max_length=255)
    organization_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="organizations.id",
        nullable=True,
        index=True,
        ondelete="CASCADE",
    )
    family: str = Field(default=Family.client.value, max_length=16, index=True)
    role: str = Field(default=Role.client_user.value, max_length=32)
    hashed_password: str
    created_at: datetime = created_at_field()
    updated_at: datetime | None = updated_at_field()


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    # Defaults to a valid org-less Unveilix-team user. Real creation flows (seed, admin UI,
    # init_db) always pass `family` explicitly; this default only keeps generic/bare
    # constructions (e.g. test helpers) valid under the family/organization rule.
    family: Family = Family.unveilix
    role: Role = Role.agent
    organization_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _check_family_org(self) -> Self:
        if self.family == Family.client and self.organization_id is None:
            raise ValueError("client-family users require an organization_id")
        if self.family == Family.unveilix and self.organization_id is not None:
            raise ValueError("unveilix-family users must not have an organization_id")
        return self


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(max_length=255)


class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore[assignment]
    full_name: str | None = Field(default=None, max_length=255)  # type: ignore[assignment]
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: Role | None = None


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserPublic(UserBase):
    id: uuid.UUID
    family: Family
    role: Role
    organization_id: uuid.UUID | None = None
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# ===========================================================================
# Tickets (the tenant-scoped core resource)
# ===========================================================================
class Ticket(SQLModel, table=True):
    __tablename__ = "tickets"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    reference: str = Field(unique=True, index=True, max_length=32)
    organization_id: uuid.UUID = Field(
        foreign_key="organizations.id", nullable=False, index=True, ondelete="CASCADE"
    )
    reporter_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False, index=True
    )
    title: str = Field(max_length=512)
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    module: str = Field(max_length=32)
    severity: str = Field(max_length=32)
    priority: str = Field(max_length=8, index=True)
    status: str = Field(default=TicketStatus.new.value, max_length=32, index=True)
    assignee_id: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", nullable=True, index=True
    )
    environment: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    # Root-cause analysis — required when the ticket is moved to `closed` (enforced in the API).
    rca: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = created_at_field()
    updated_at: datetime | None = updated_at_field()
    closed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    attachments: list["Attachment"] = Relationship(
        back_populates="ticket", cascade_delete=True
    )
    comments: list["Comment"] = Relationship(
        back_populates="ticket", cascade_delete=True
    )
    activity: list["Activity"] = Relationship(
        back_populates="ticket", cascade_delete=True
    )


class TicketCreate(SQLModel):
    title: str = Field(min_length=1, max_length=512)
    description: str | None = None
    module: Module
    severity: Severity
    environment: dict[str, Any] | None = None
    # Team users must specify which org; ignored for client users (their own org is used).
    organization_id: uuid.UUID | None = None


class TicketUpdate(SQLModel):
    """Team-only edits. Use exclude_unset to tell 'not provided' from 'set to null'."""

    status: TicketStatus | None = None
    priority: Priority | None = None
    assignee_id: uuid.UUID | None = None
    # Root-cause analysis. Required (here or already present) when status -> closed.
    rca: str | None = None


class TicketSummary(SQLModel):
    id: uuid.UUID
    reference: str
    organization_id: uuid.UUID
    organization_name: str
    title: str
    module: Module
    severity: Severity
    priority: Priority
    status: TicketStatus
    reporter_id: uuid.UUID
    reporter_name: str | None = None
    assignee_id: uuid.UUID | None = None
    assignee_name: str | None = None
    attachment_count: int = 0
    comment_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None
    closed_at: datetime | None = None


class TicketsPublic(SQLModel):
    data: list[TicketSummary]
    count: int


class TicketBoard(SQLModel):
    """Tickets grouped by status column for the Kanban (spec §4)."""

    columns: dict[str, list[TicketSummary]]


# ===========================================================================
# Attachments
# ===========================================================================
class Attachment(SQLModel, table=True):
    __tablename__ = "attachments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    ticket_id: uuid.UUID = Field(
        foreign_key="tickets.id", nullable=False, index=True, ondelete="CASCADE"
    )
    kind: str = Field(max_length=16)
    filename: str = Field(max_length=512)
    content_type: str = Field(max_length=128)
    # spec §3: size_bytes is BIGINT
    size_bytes: int | None = Field(
        default=None, sa_column=Column(BigInteger, nullable=True)
    )
    storage_path: str = Field(max_length=1024)
    created_at: datetime = created_at_field()

    ticket: Ticket | None = Relationship(back_populates="attachments")


class AttachmentPublic(SQLModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    kind: AttachmentKind
    filename: str
    content_type: str
    size_bytes: int | None = None
    created_at: datetime


# ===========================================================================
# Comments (internal notes are NEVER serialized to client-family responses)
# ===========================================================================
class Comment(SQLModel, table=True):
    __tablename__ = "comments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    ticket_id: uuid.UUID = Field(
        foreign_key="tickets.id", nullable=False, index=True, ondelete="CASCADE"
    )
    author_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    body: str = Field(sa_column=Column(Text, nullable=False))
    is_internal: bool = Field(default=False)
    created_at: datetime = created_at_field()

    ticket: Ticket | None = Relationship(back_populates="comments")


class CommentCreate(SQLModel):
    body: str = Field(min_length=1)
    is_internal: bool = False


class CommentPublic(SQLModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    author_id: uuid.UUID
    author_name: str | None = None
    body: str
    is_internal: bool
    created_at: datetime


# ===========================================================================
# Activity (audit trail / timeline)
# ===========================================================================
class Activity(SQLModel, table=True):
    __tablename__ = "activity"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    ticket_id: uuid.UUID = Field(
        foreign_key="tickets.id", nullable=False, index=True, ondelete="CASCADE"
    )
    actor_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    action: str = Field(max_length=32)
    detail: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    created_at: datetime = created_at_field()

    ticket: Ticket | None = Relationship(back_populates="activity")


class ActivityPublic(SQLModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    actor_id: uuid.UUID
    actor_name: str | None = None
    action: ActivityAction
    detail: dict[str, Any] | None = None
    created_at: datetime


# ===========================================================================
# Ticket detail (assembled response: ticket + attachments + comments + timeline)
# ===========================================================================
class TicketDetail(TicketSummary):
    description: str | None = None
    environment: dict[str, Any] | None = None
    rca: str | None = None
    attachments: list[AttachmentPublic] = []
    comments: list[CommentPublic] = []
    activity: list[ActivityPublic] = []


# ===========================================================================
# Dashboard stats (team only — spec §4)
# ===========================================================================
class DashboardStats(SQLModel):
    open_count: int
    breaching_sla_count: int
    deployed_last_7d: int
    median_resolution_days: float | None = None


# ===========================================================================
# Generic / auth payloads (kept from template)
# ===========================================================================
class Message(SQLModel):
    message: str


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(SQLModel):
    email: EmailStr
    password: str


class LoginResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
