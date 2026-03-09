"""add status to project_phases, remove from phases

Revision ID: 20260309_0001
Revises: 20260308_0002
Create Date: 2026-03-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260309_0001"
down_revision: str | None = "20260308_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "project_phases",
        sa.Column("status", sa.String(20), server_default="not_started", nullable=False),
    )
    op.drop_column("phases", "status")


def downgrade() -> None:
    op.add_column(
        "phases",
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
    )
    op.drop_column("project_phases", "status")
