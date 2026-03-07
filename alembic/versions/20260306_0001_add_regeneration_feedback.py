"""add regeneration_feedback column to book_context_documents

Revision ID: 20260306_0001
Revises: 20260305_0002
Create Date: 2026-03-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260306_0001"
down_revision: str | None = "20260305_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "book_context_documents",
        sa.Column("regeneration_feedback", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("book_context_documents", "regeneration_feedback")
