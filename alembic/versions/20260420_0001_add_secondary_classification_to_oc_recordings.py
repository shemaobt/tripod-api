"""add secondary classification columns to oc_recordings

Revision ID: 20260420_0001
Revises: 20260415_0001
Create Date: 2026-04-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260420_0001"
down_revision: str | None = "20260415_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "oc_recordings",
        sa.Column("secondary_genre_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "oc_recordings",
        sa.Column("secondary_subcategory_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "oc_recordings",
        sa.Column("secondary_register_id", sa.String(50), nullable=True),
    )
    op.create_foreign_key(
        "fk_oc_recordings_secondary_genre_id",
        "oc_recordings",
        "oc_genres",
        ["secondary_genre_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_oc_recordings_secondary_subcategory_id",
        "oc_recordings",
        "oc_subcategories",
        ["secondary_subcategory_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_oc_recordings_secondary_subcategory_id",
        "oc_recordings",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_oc_recordings_secondary_genre_id",
        "oc_recordings",
        type_="foreignkey",
    )
    op.drop_column("oc_recordings", "secondary_register_id")
    op.drop_column("oc_recordings", "secondary_subcategory_id")
    op.drop_column("oc_recordings", "secondary_genre_id")
