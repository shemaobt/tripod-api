"""add locked_by and locked_at columns to book_context_documents

Revision ID: 20260327_0001
Revises: 20260318_0001
Create Date: 2026-03-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260327_0001"
down_revision: str | None = "20260318_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "book_context_documents",
        sa.Column("locked_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "book_context_documents",
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("book_context_documents", "locked_at")
    op.drop_column("book_context_documents", "locked_by")
