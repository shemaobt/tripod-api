"""backfill project-health bootstrap admin grant

Revision ID: 20260518_0002
Revises: 20260518_0001
Create Date: 2026-05-18 20:00:00.000000

The original 20260518_0001 migration tries to grant the project-health
admin role to the bootstrap email at migration time, but skips silently
if the user row does not yet exist. In production the migration ran
before any user had been created, so the grant was a no-op. This
migration retries the grant idempotently: if the user now exists and
does not already hold the admin role, the grant lands; otherwise it is
a no-op.
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "20260518_0002"
down_revision: str | None = "20260518_0001"
branch_labels = None
depends_on = None


PH_APP_KEY = "project-health"
PH_ADMIN_ROLE_KEY = "admin"
BOOTSTRAP_ADMIN_EMAIL = "shema.apps@ywambt.com"


def upgrade() -> None:
    bind = op.get_bind()

    user_id = bind.execute(
        sa.text("SELECT id FROM users WHERE email = :email"),
        {"email": BOOTSTRAP_ADMIN_EMAIL},
    ).scalar()
    if user_id is None:
        return

    app_id = bind.execute(
        sa.text("SELECT id FROM apps WHERE app_key = :app_key"),
        {"app_key": PH_APP_KEY},
    ).scalar()
    if app_id is None:
        return

    role_id = bind.execute(
        sa.text(
            "SELECT id FROM roles WHERE app_id = :app_id AND role_key = :role_key"
        ),
        {"app_id": app_id, "role_key": PH_ADMIN_ROLE_KEY},
    ).scalar()
    if role_id is None:
        return

    already_granted = bind.execute(
        sa.text(
            "SELECT id FROM user_app_roles "
            "WHERE user_id = :user_id AND app_id = :app_id "
            "AND role_id = :role_id AND revoked_at IS NULL"
        ),
        {"user_id": user_id, "app_id": app_id, "role_id": role_id},
    ).scalar()
    if already_granted is not None:
        return

    bind.execute(
        sa.text(
            "INSERT INTO user_app_roles (id, user_id, app_id, role_id) "
            "VALUES (:id, :user_id, :app_id, :role_id)"
        ),
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "app_id": app_id,
            "role_id": role_id,
        },
    )


def downgrade() -> None:
    # No-op: the original 20260518_0001 migration's downgrade already deletes
    # every user_app_roles row tied to the project-health app's roles, which
    # covers this backfill grant too. Re-deleting here would double-execute.
    pass
