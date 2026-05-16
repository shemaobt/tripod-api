"""add translation-helper tables and seed app/role

Revision ID: 20260516_0001
Revises: 20260420_0003
Create Date: 2026-05-16 12:00:00.000000
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "20260516_0001"
down_revision: str | None = "20260420_0003"
branch_labels = None
depends_on = None


TH_APP_KEY = "translation-helper"
TH_APP_NAME = "Translation Helper"
TH_APP_DESCRIPTION = (
    "Conversational AI assistants for Bible translation: storyteller, "
    "conversation partner, oral performer, project-health assessor, and "
    "back-translation checker."
)
TH_USER_ROLE_KEY = "user"
TH_USER_ROLE_LABEL = "User"


def upgrade() -> None:
    op.create_table(
        "th_chats",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "agent_id",
            sa.Enum(
                "storyteller",
                "conversation",
                "oral",
                "health",
                "backtrans",
                name="th_agent_id_enum",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_th_chats_user_id"), "th_chats", ["user_id"], unique=False)
    op.create_index(
        "ix_th_chats_user_updated", "th_chats", ["user_id", "updated_at"], unique=False
    )

    op.create_table(
        "th_chat_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("chat_id", sa.String(length=36), nullable=False),
        sa.Column(
            "role",
            sa.Enum("user", "assistant", name="th_chat_message_role_enum"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "agent_id",
            sa.Enum(
                "storyteller",
                "conversation",
                "oral",
                "health",
                "backtrans",
                name="th_agent_id_enum",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chat_id"], ["th_chats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_th_chat_messages_chat_id"), "th_chat_messages", ["chat_id"], unique=False
    )
    op.create_index(
        "ix_th_chat_messages_chat_created",
        "th_chat_messages",
        ["chat_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "th_agent_prompts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", name="uq_th_agent_prompts_agent_id"),
    )
    op.create_index(
        op.f("ix_th_agent_prompts_agent_id"), "th_agent_prompts", ["agent_id"], unique=False
    )

    bind = op.get_bind()
    app_id = bind.execute(
        sa.text("SELECT id FROM apps WHERE app_key = :app_key"),
        {"app_key": TH_APP_KEY},
    ).scalar()
    if app_id is None:
        app_id = str(uuid.uuid4())
        bind.execute(
            sa.text(
                "INSERT INTO apps (id, app_key, name, description, platform, is_active) "
                "VALUES (:id, :app_key, :name, :description, :platform, TRUE)"
            ),
            {
                "id": app_id,
                "app_key": TH_APP_KEY,
                "name": TH_APP_NAME,
                "description": TH_APP_DESCRIPTION,
                "platform": "web",
            },
        )

    role_exists = bind.execute(
        sa.text("SELECT id FROM roles WHERE app_id = :app_id AND role_key = :role_key"),
        {"app_id": app_id, "role_key": TH_USER_ROLE_KEY},
    ).scalar()
    if role_exists is None:
        bind.execute(
            sa.text(
                "INSERT INTO roles (id, app_id, role_key, label, description, is_system) "
                "VALUES (:id, :app_id, :role_key, :label, :description, TRUE)"
            ),
            {
                "id": str(uuid.uuid4()),
                "app_id": app_id,
                "role_key": TH_USER_ROLE_KEY,
                "label": TH_USER_ROLE_LABEL,
                "description": "Default access role for Translation Helper users.",
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    app_id = bind.execute(
        sa.text("SELECT id FROM apps WHERE app_key = :app_key"),
        {"app_key": TH_APP_KEY},
    ).scalar()
    if app_id is not None:
        bind.execute(
            sa.text("DELETE FROM roles WHERE app_id = :app_id"), {"app_id": app_id}
        )
        bind.execute(sa.text("DELETE FROM apps WHERE id = :id"), {"id": app_id})

    op.drop_index(op.f("ix_th_agent_prompts_agent_id"), table_name="th_agent_prompts")
    op.drop_table("th_agent_prompts")

    op.drop_index("ix_th_chat_messages_chat_created", table_name="th_chat_messages")
    op.drop_index(op.f("ix_th_chat_messages_chat_id"), table_name="th_chat_messages")
    op.drop_table("th_chat_messages")

    op.drop_index("ix_th_chats_user_updated", table_name="th_chats")
    op.drop_index(op.f("ix_th_chats_user_id"), table_name="th_chats")
    op.drop_table("th_chats")

    bind.execute(sa.text("DROP TYPE IF EXISTS th_agent_id_enum"))
    bind.execute(sa.text("DROP TYPE IF EXISTS th_chat_message_role_enum"))
