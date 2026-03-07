"""seed specialist roles for meaning-map-generator

Revision ID: 20260306_0003
Revises: 20260306_0002
Create Date: 2026-03-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260306_0003"
down_revision: str | None = "20260306_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SPECIALIST_ROLES = [
    ("exegete", "Exegete"),
    ("biblical_language_specialist", "Biblical Language Specialist"),
    ("translation_specialist", "Translation Specialist"),
]


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT id FROM apps WHERE app_key = 'meaning-map-generator'")
    )
    row = result.fetchone()
    if not row:
        return
    app_id = row[0]

    for role_key, label in SPECIALIST_ROLES:
        exists = conn.execute(
            sa.text("SELECT id FROM roles WHERE app_id = :app_id AND role_key = :role_key"),
            {"app_id": app_id, "role_key": role_key},
        ).fetchone()
        if not exists:
            conn.execute(
                sa.text(
                    "INSERT INTO roles (id, app_id, role_key, label, is_system) "
                    "VALUES (gen_random_uuid(), :app_id, :role_key, :label, true)"
                ),
                {"app_id": app_id, "role_key": role_key, "label": label},
            )


def downgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT id FROM apps WHERE app_key = 'meaning-map-generator'")
    )
    row = result.fetchone()
    if not row:
        return
    app_id = row[0]

    for role_key, _ in SPECIALIST_ROLES:
        conn.execute(
            sa.text("DELETE FROM roles WHERE app_id = :app_id AND role_key = :role_key"),
            {"app_id": app_id, "role_key": role_key},
        )
