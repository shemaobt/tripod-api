"""add new-language fields to change_requests

Revision ID: 20260709_0002
Revises: 20260709_0001
Create Date: 2026-07-09

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260709_0002"
down_revision: str | None = "20260709_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {col["name"] for col in sa.inspect(bind).get_columns("change_requests")}
    if "new_language_name" not in columns:
        op.add_column(
            "change_requests", sa.Column("new_language_name", sa.String(200), nullable=True)
        )
    if "new_language_code" not in columns:
        op.add_column(
            "change_requests", sa.Column("new_language_code", sa.String(3), nullable=True)
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {col["name"] for col in sa.inspect(bind).get_columns("change_requests")}
    if "new_language_code" in columns:
        op.drop_column("change_requests", "new_language_code")
    if "new_language_name" in columns:
        op.drop_column("change_requests", "new_language_name")
