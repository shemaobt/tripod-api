"""add book_context_documents, bcd_approvals, bcd_section_feedback, bcd_generation_logs

Revision ID: 20260305_0001
Revises: 20260304_0001
Create Date: 2026-03-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260305_0001"
down_revision: str | None = "20260304_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

bcd_status_enum = postgresql.ENUM(
    "generating", "draft", "review", "approved",
    name="bcd_status_enum", create_type=False,
)


def upgrade() -> None:
    conn = op.get_bind()
    # Create enum type idempotently (handles orphaned type from prior failed migration)
    conn.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE bcd_status_enum AS ENUM ('generating', 'draft', 'review', 'approved'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$"
    ))

    op.create_table(
        "book_context_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "book_id",
            sa.String(36),
            sa.ForeignKey("bible_books.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("section_label", sa.String(100), nullable=True),
        sa.Column("section_range_start", sa.Integer, nullable=True),
        sa.Column("section_range_end", sa.Integer, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", bcd_status_enum, nullable=False, server_default="draft"),
        sa.Column("structural_outline", sa.JSON, nullable=True),
        sa.Column("participant_register", sa.JSON, nullable=True),
        sa.Column("discourse_threads", sa.JSON, nullable=True),
        sa.Column("theological_spine", sa.Text, nullable=True),
        sa.Column("places", sa.JSON, nullable=True),
        sa.Column("objects", sa.JSON, nullable=True),
        sa.Column("institutions", sa.JSON, nullable=True),
        sa.Column("genre_context", sa.JSON, nullable=True),
        sa.Column("maintenance_notes", sa.JSON, nullable=True),
        sa.Column("generation_metadata", sa.JSON, nullable=True),
        sa.Column(
            "prepared_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "book_id",
            "section_range_start",
            "section_range_end",
            "version",
            name="uq_bcd_book_section_version",
        ),
    )
    op.create_index(
        "ix_bcd_book_status",
        "book_context_documents",
        ["book_id", "status"],
    )

    op.create_table(
        "bcd_approvals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "bcd_id",
            sa.String(36),
            sa.ForeignKey("book_context_documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("role_at_approval", sa.String(50), nullable=False),
        sa.Column(
            "approved_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("bcd_id", "user_id", name="uq_bcd_approval_user"),
    )

    op.create_table(
        "bcd_section_feedback",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "bcd_id",
            sa.String(36),
            sa.ForeignKey("book_context_documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("section_key", sa.String(50), nullable=False),
        sa.Column(
            "author_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "bcd_generation_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "bcd_id",
            sa.String(36),
            sa.ForeignKey("book_context_documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("step_name", sa.String(100), nullable=False),
        sa.Column("step_order", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("input_summary", sa.Text, nullable=True),
        sa.Column("output_summary", sa.Text, nullable=True),
        sa.Column("token_count", sa.Integer, nullable=True),
        sa.Column("error_detail", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.add_column(
        "meaning_maps",
        sa.Column("bcd_version_at_creation", sa.Integer, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meaning_maps", "bcd_version_at_creation")
    op.drop_table("bcd_generation_logs")
    op.drop_table("bcd_section_feedback")
    op.drop_table("bcd_approvals")
    op.drop_index("ix_bcd_book_status", table_name="book_context_documents")
    op.drop_table("book_context_documents")
    bcd_status_enum.drop(op.get_bind(), checkfirst=True)
