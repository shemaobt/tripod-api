"""add ph_agent_prompts table

Revision ID: 20260519_0001
Revises: 20260518_0002
Create Date: 2026-05-19 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20260519_0001"
down_revision: str | None = "20260518_0002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "ph_agent_prompts",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("prompt_key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "updated_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("prompt_key", name="uq_ph_agent_prompts_prompt_key"),
    )
    op.create_index(
        op.f("ix_ph_agent_prompts_prompt_key"),
        "ph_agent_prompts",
        ["prompt_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ph_agent_prompts_prompt_key"), table_name="ph_agent_prompts")
    op.drop_table("ph_agent_prompts")
