"""add is_active column to book_context_documents

Revision ID: 20260305_0002
Revises: 20260305_0001
Create Date: 2026-03-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260305_0002"
down_revision: str | None = "20260305_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "book_context_documents",
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_index(
        "ix_bcd_book_active",
        "book_context_documents",
        ["book_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bcd_book_active", table_name="book_context_documents")
    op.drop_column("book_context_documents", "is_active")
