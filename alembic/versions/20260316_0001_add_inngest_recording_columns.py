"""add upload_error, cleaning_error, splitting_status, split_from_id to oc_recordings

Revision ID: 20260316_0001
Revises: 20260312_0001
Create Date: 2026-03-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260316_0001"
down_revision: str | None = "20260312_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("oc_recordings", sa.Column("upload_error", sa.Text(), nullable=True))
    op.add_column("oc_recordings", sa.Column("cleaning_error", sa.Text(), nullable=True))
    op.add_column(
        "oc_recordings",
        sa.Column("splitting_status", sa.String(20), nullable=False, server_default="none"),
    )
    op.add_column(
        "oc_recordings", sa.Column("split_from_id", sa.String(36), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("oc_recordings", "split_from_id")
    op.drop_column("oc_recordings", "splitting_status")
    op.drop_column("oc_recordings", "cleaning_error")
    op.drop_column("oc_recordings", "upload_error")
