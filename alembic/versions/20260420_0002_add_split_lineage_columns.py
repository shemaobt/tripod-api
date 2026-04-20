"""add split_index and split_segment_count to oc_recordings

Revision ID: 20260420_0002
Revises: 20260420_0001
Create Date: 2026-04-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260420_0002"
down_revision: str | None = "20260420_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "oc_recordings",
        sa.Column("split_index", sa.Integer(), nullable=True),
    )
    op.add_column(
        "oc_recordings",
        sa.Column("split_segment_count", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_oc_recordings_split_from_id",
        "oc_recordings",
        ["split_from_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_oc_recordings_split_from_id", table_name="oc_recordings")
    op.drop_column("oc_recordings", "split_segment_count")
    op.drop_column("oc_recordings", "split_index")
