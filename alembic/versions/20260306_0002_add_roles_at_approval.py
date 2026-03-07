"""add roles_at_approval JSON column to bcd_approvals

Revision ID: 20260306_0002
Revises: 20260306_0001
Create Date: 2026-03-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260306_0002"
down_revision: str | None = "20260306_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bcd_approvals",
        sa.Column("roles_at_approval", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bcd_approvals", "roles_at_approval")
