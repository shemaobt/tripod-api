"""add reviewer_locale column to bcd_approvals

Revision ID: 20260327_0002
Revises: 20260327_0001
Create Date: 2026-03-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260327_0002"
down_revision: str | None = "20260327_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bcd_approvals",
        sa.Column("reviewer_locale", sa.String(10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bcd_approvals", "reviewer_locale")
