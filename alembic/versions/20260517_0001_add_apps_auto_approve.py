"""add auto_approve column to apps table

Revision ID: 20260517_0001
Revises: 20260516_0001
Create Date: 2026-05-17 12:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20260517_0001"
down_revision: str | None = "20260516_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "apps",
        sa.Column(
            "auto_approve",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("apps", "auto_approve")
