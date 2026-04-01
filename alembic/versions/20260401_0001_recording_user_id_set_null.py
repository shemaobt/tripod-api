"""change oc_recordings.user_id FK to SET NULL on delete

Revision ID: 20260401_0001
Revises: 20260327_0003
Create Date: 2026-04-01

"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260401_0001"
down_revision: str | None = "20260327_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("oc_recordings_user_id_fkey", "oc_recordings", type_="foreignkey")
    op.alter_column("oc_recordings", "user_id", nullable=True)
    op.create_foreign_key(
        "oc_recordings_user_id_fkey",
        "oc_recordings",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("oc_recordings_user_id_fkey", "oc_recordings", type_="foreignkey")
    op.alter_column("oc_recordings", "user_id", nullable=False)
    op.create_foreign_key(
        "oc_recordings_user_id_fkey",
        "oc_recordings",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
