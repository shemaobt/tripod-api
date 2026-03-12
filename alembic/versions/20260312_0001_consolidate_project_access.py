"""consolidate OC project membership into shared tables

Revision ID: 20260312_0001
Revises: 20260309_0003
Create Date: 2026-03-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260312_0001"
down_revision: str | None = "20260309_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- 1. Add role + invited_by columns to project_user_access ---
    op.add_column(
        "project_user_access",
        sa.Column("role", sa.String(30), nullable=False, server_default="member"),
    )
    op.add_column(
        "project_user_access",
        sa.Column(
            "invited_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # --- 2. Create project_invites table ---
    op.create_table(
        "project_invites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column(
            "invited_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("role", sa.String(30), nullable=False, server_default="member"),
        sa.Column("app_key", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- 3. Migrate oc_project_users → project_user_access ---
    conn = op.get_bind()

    # Fetch all OC membership rows
    oc_members = conn.execute(
        sa.text("SELECT project_id, user_id, role, invited_by FROM oc_project_users")
    ).fetchall()

    for row in oc_members:
        mapped_role = "manager" if row.role == "project_manager" else "member"

        # Check if (project_id, user_id) already exists in project_user_access
        existing = conn.execute(
            sa.text(
                "SELECT id FROM project_user_access "
                "WHERE project_id = :pid AND user_id = :uid"
            ),
            {"pid": row.project_id, "uid": row.user_id},
        ).fetchone()

        if existing:
            # Update role and invited_by on existing row
            conn.execute(
                sa.text(
                    "UPDATE project_user_access "
                    "SET role = :role, invited_by = :invited_by "
                    "WHERE id = :id"
                ),
                {"role": mapped_role, "invited_by": row.invited_by, "id": existing.id},
            )
        else:
            # Insert new row
            import uuid

            conn.execute(
                sa.text(
                    "INSERT INTO project_user_access "
                    "(id, project_id, user_id, role, invited_by) "
                    "VALUES (:id, :pid, :uid, :role, :invited_by)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "pid": row.project_id,
                    "uid": row.user_id,
                    "role": mapped_role,
                    "invited_by": row.invited_by,
                },
            )

    # --- 4. Migrate oc_project_invites → project_invites ---
    oc_invites = conn.execute(
        sa.text(
            "SELECT id, project_id, email, invited_by, status, role, "
            "created_at, accepted_at FROM oc_project_invites"
        )
    ).fetchall()

    for inv in oc_invites:
        mapped_role = "manager" if inv.role == "project_manager" else "member"
        conn.execute(
            sa.text(
                "INSERT INTO project_invites "
                "(id, project_id, email, invited_by, status, role, app_key, "
                "created_at, accepted_at) "
                "VALUES (:id, :pid, :email, :invited_by, :status, :role, "
                "'oral-collector', :created_at, :accepted_at)"
            ),
            {
                "id": inv.id,
                "pid": inv.project_id,
                "email": inv.email,
                "invited_by": inv.invited_by,
                "status": inv.status,
                "role": mapped_role,
                "created_at": inv.created_at,
                "accepted_at": inv.accepted_at,
            },
        )

    # --- 5. Drop old OC tables ---
    op.drop_table("oc_project_invites")
    op.drop_table("oc_project_users")


def downgrade() -> None:
    # Re-create oc_project_users
    op.create_table(
        "oc_project_users",
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(30), nullable=False, server_default="user"),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "invited_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Re-create oc_project_invites
    op.create_table(
        "oc_project_invites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column(
            "invited_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("role", sa.String(30), nullable=False, server_default="user"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Drop project_invites
    op.drop_table("project_invites")

    # Remove added columns from project_user_access
    op.drop_column("project_user_access", "invited_by")
    op.drop_column("project_user_access", "role")
