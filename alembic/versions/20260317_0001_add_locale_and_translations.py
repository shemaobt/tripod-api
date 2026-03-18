"""add locale to users and translations to meaning_maps and book_context_documents

Revision ID: a1b2c3d4e5f6
Revises: 20260316_0001_add_inngest_recording_columns
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa

revision = "20260317_0001"
down_revision = "20260316_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("locale", sa.String(10), nullable=True))
    op.add_column("meaning_maps", sa.Column("translations", sa.JSON(), nullable=True))
    op.add_column("book_context_documents", sa.Column("translations", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("book_context_documents", "translations")
    op.drop_column("meaning_maps", "translations")
    op.drop_column("users", "locale")
