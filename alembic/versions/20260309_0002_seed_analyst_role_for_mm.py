"""seed analyst role for meaning-map-generator app

Revision ID: 20260309_0002
Revises: 20260309_0001
Create Date: 2026-03-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260309_0002"
down_revision: str | None = "20260309_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    app_row = conn.execute(
        sa.text("SELECT id FROM apps WHERE app_key = 'meaning-map-generator'")
    ).first()
    if not app_row:
        return

    app_id = app_row[0]

    existing = conn.execute(
        sa.text("SELECT id FROM roles WHERE app_id = :app_id AND role_key = 'analyst'"),
        {"app_id": app_id},
    ).first()
    if not existing:
        import uuid

        conn.execute(
            sa.text(
                "INSERT INTO roles (id, app_id, role_key, label, is_system) "
                "VALUES (:id, :app_id, 'analyst', 'Analyst', true)"
            ),
            {"id": str(uuid.uuid4()), "app_id": app_id},
        )


def downgrade() -> None:
    conn = op.get_bind()
    app_row = conn.execute(
        sa.text("SELECT id FROM apps WHERE app_key = 'meaning-map-generator'")
    ).first()
    if not app_row:
        return
    conn.execute(
        sa.text("DELETE FROM roles WHERE app_id = :app_id AND role_key = 'analyst'"),
        {"app_id": app_row[0]},
    )
