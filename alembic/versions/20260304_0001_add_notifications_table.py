"""add notifications and notification_meaning_map_details tables

Revision ID: 20260304_0001
Revises: 20260303_0002
Create Date: 2026-03-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260304_0001"
down_revision: str | None = "20260303_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "app_id",
            sa.String(36),
            sa.ForeignKey("apps.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column(
            "actor_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_notifications_user_app_unread_created",
        "notifications",
        ["user_id", "app_id", "is_read", "created_at"],
    )

    op.create_table(
        "notification_meaning_map_details",
        sa.Column(
            "notification_id",
            sa.String(36),
            sa.ForeignKey("notifications.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "related_map_id",
            sa.String(36),
            sa.ForeignKey("meaning_maps.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("pericope_reference", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("notification_meaning_map_details")
    op.drop_index("ix_notifications_user_app_unread_created", table_name="notifications")
    op.drop_table("notifications")
