"""add description, logo_url, manager_id to organizations

Revision ID: 20260308_0002
Revises: 20260308_0001
Create Date: 2026-03-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260308_0002"
down_revision: str | None = "20260308_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("description", sa.String(500), nullable=True))
    op.add_column("organizations", sa.Column("logo_url", sa.String(500), nullable=True))
    op.add_column("organizations", sa.Column("manager_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "manager_id")
    op.drop_column("organizations", "logo_url")
    op.drop_column("organizations", "description")
