"""add project-health tables and seed app/roles

Revision ID: 20260518_0001
Revises: 20260517_0001
Create Date: 2026-05-18 12:00:00.000000
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision: str = "20260518_0001"
down_revision: str | None = "20260517_0001"
branch_labels = None
depends_on = None


PH_APP_KEY = "project-health"
PH_APP_NAME = "Project Health"
PH_APP_DESCRIPTION = (
    "Conversational OBT sustainability interviews with multilingual facilitation "
    "and structured team/admin reports across seven health domains."
)
PH_USER_ROLE_KEY = "user"
PH_USER_ROLE_LABEL = "User"
PH_USER_ROLE_DESCRIPTION = "Authenticated team member who can run interviews."
PH_ADMIN_ROLE_KEY = "admin"
PH_ADMIN_ROLE_LABEL = "Admin"
PH_ADMIN_ROLE_DESCRIPTION = (
    "Sees the dashboard, reviews all reports, and invites other admins."
)
BOOTSTRAP_ADMIN_EMAIL = "shema.apps@ywambt.com"


def upgrade() -> None:
    op.create_table(
        "ph_interviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_name", sa.String(length=200), nullable=False),
        sa.Column("team_name", sa.String(length=200), nullable=False),
        sa.Column(
            "language",
            sa.Enum("en", "pt", "es", "fr", "id", "sw", name="ph_language_enum"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "in_progress",
                "completed",
                "abandoned",
                name="ph_interview_status_enum",
            ),
            nullable=False,
        ),
        sa.Column(
            "messages",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "coverage_state",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "evidence",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ph_interviews_status_created",
        "ph_interviews",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "ph_reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("interview_id", sa.String(length=36), nullable=False),
        sa.Column(
            "team_report",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "admin_report",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["interview_id"], ["ph_interviews.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("interview_id", name="uq_ph_reports_interview_id"),
    )
    op.create_index(
        "ix_ph_reports_interview_id", "ph_reports", ["interview_id"], unique=False
    )

    bind = op.get_bind()

    app_id = bind.execute(
        sa.text("SELECT id FROM apps WHERE app_key = :app_key"),
        {"app_key": PH_APP_KEY},
    ).scalar()
    if app_id is None:
        app_id = str(uuid.uuid4())
        bind.execute(
            sa.text(
                "INSERT INTO apps (id, app_key, name, description, platform, "
                "is_active, auto_approve) "
                "VALUES (:id, :app_key, :name, :description, :platform, TRUE, FALSE)"
            ),
            {
                "id": app_id,
                "app_key": PH_APP_KEY,
                "name": PH_APP_NAME,
                "description": PH_APP_DESCRIPTION,
                "platform": "web",
            },
        )

    user_role_id = bind.execute(
        sa.text("SELECT id FROM roles WHERE app_id = :app_id AND role_key = :role_key"),
        {"app_id": app_id, "role_key": PH_USER_ROLE_KEY},
    ).scalar()
    if user_role_id is None:
        user_role_id = str(uuid.uuid4())
        bind.execute(
            sa.text(
                "INSERT INTO roles (id, app_id, role_key, label, description, is_system) "
                "VALUES (:id, :app_id, :role_key, :label, :description, TRUE)"
            ),
            {
                "id": user_role_id,
                "app_id": app_id,
                "role_key": PH_USER_ROLE_KEY,
                "label": PH_USER_ROLE_LABEL,
                "description": PH_USER_ROLE_DESCRIPTION,
            },
        )

    admin_role_id = bind.execute(
        sa.text("SELECT id FROM roles WHERE app_id = :app_id AND role_key = :role_key"),
        {"app_id": app_id, "role_key": PH_ADMIN_ROLE_KEY},
    ).scalar()
    if admin_role_id is None:
        admin_role_id = str(uuid.uuid4())
        bind.execute(
            sa.text(
                "INSERT INTO roles (id, app_id, role_key, label, description, is_system) "
                "VALUES (:id, :app_id, :role_key, :label, :description, TRUE)"
            ),
            {
                "id": admin_role_id,
                "app_id": app_id,
                "role_key": PH_ADMIN_ROLE_KEY,
                "label": PH_ADMIN_ROLE_LABEL,
                "description": PH_ADMIN_ROLE_DESCRIPTION,
            },
        )

    bootstrap_user_id = bind.execute(
        sa.text("SELECT id FROM users WHERE email = :email"),
        {"email": BOOTSTRAP_ADMIN_EMAIL},
    ).scalar()
    if bootstrap_user_id is not None:
        existing_grant = bind.execute(
            sa.text(
                "SELECT id FROM user_app_roles "
                "WHERE user_id = :user_id AND app_id = :app_id "
                "AND role_id = :role_id AND revoked_at IS NULL"
            ),
            {
                "user_id": bootstrap_user_id,
                "app_id": app_id,
                "role_id": admin_role_id,
            },
        ).scalar()
        if existing_grant is None:
            bind.execute(
                sa.text(
                    "INSERT INTO user_app_roles (id, user_id, app_id, role_id) "
                    "VALUES (:id, :user_id, :app_id, :role_id)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "user_id": bootstrap_user_id,
                    "app_id": app_id,
                    "role_id": admin_role_id,
                },
            )


def downgrade() -> None:
    bind = op.get_bind()
    app_id = bind.execute(
        sa.text("SELECT id FROM apps WHERE app_key = :app_key"),
        {"app_key": PH_APP_KEY},
    ).scalar()
    if app_id is not None:
        role_ids = [
            row[0]
            for row in bind.execute(
                sa.text("SELECT id FROM roles WHERE app_id = :app_id"),
                {"app_id": app_id},
            )
        ]
        if role_ids:
            bind.execute(
                sa.text(
                    "DELETE FROM user_app_roles WHERE role_id = ANY(:role_ids)"
                ),
                {"role_ids": role_ids},
            )
        bind.execute(
            sa.text("DELETE FROM access_requests WHERE app_id = :app_id"),
            {"app_id": app_id},
        )
        bind.execute(
            sa.text("DELETE FROM roles WHERE app_id = :app_id"), {"app_id": app_id}
        )
        bind.execute(sa.text("DELETE FROM apps WHERE id = :id"), {"id": app_id})

    op.drop_index("ix_ph_reports_interview_id", table_name="ph_reports")
    op.drop_table("ph_reports")

    op.drop_index("ix_ph_interviews_status_created", table_name="ph_interviews")
    op.drop_table("ph_interviews")

    bind.execute(sa.text("DROP TYPE IF EXISTS ph_interview_status_enum"))
    bind.execute(sa.text("DROP TYPE IF EXISTS ph_language_enum"))
