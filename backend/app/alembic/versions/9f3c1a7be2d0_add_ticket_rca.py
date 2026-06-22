"""add ticket rca (root-cause analysis)

Revision ID: 9f3c1a7be2d0
Revises: b8691bbba9a0
Create Date: 2026-06-22

[#001] 2026-06-22 — Sumeet — Additive migration: a nullable `rca` text column on tickets,
populated when a ticket is closed (required-at-close enforced in the API).
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9f3c1a7be2d0"
down_revision = "b8691bbba9a0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tickets", sa.Column("rca", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("tickets", "rca")
