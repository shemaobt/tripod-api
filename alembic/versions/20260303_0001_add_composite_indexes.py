"""add composite indexes for query performance

Revision ID: 20260303_0001
Revises: 24dc98b94ae1
Create Date: 2026-03-03

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260303_0001"
down_revision: str | None = "24dc98b94ae1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_pericopes_book_chapter",
        "pericopes",
        ["book_id", "chapter_start", "verse_start"],
    )
    op.create_index(
        "ix_meaning_maps_status",
        "meaning_maps",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_meaning_maps_status", table_name="meaning_maps")
    op.drop_index("ix_pericopes_book_chapter", table_name="pericopes")
