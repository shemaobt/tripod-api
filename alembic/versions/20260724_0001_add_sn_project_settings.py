"""add sn_project_settings

The bead granularity a project cuts at. beadSec defines the bead grid and is mixed into
manifest_id, so it is the coordinate system the downstream pipeline and the training data
are built on; choosing it per session, as the SPA's setup screen did, let two audios of
one project land on two incompatible grids.

bead_sec is nullable and is not what an admin sets. The admin sets a LEVEL; the resolved
duration is granularity_frames[level] × hop_sec off each audio's own acousteme (the O8
rule), so nothing knows it until an audio is cut. The project's first session stamps it,
and from then on it is what later audios have to agree with.

No backfill. Existing projects get their row from their next session — create_session
writes the level it was cut at when no row exists — and a project with sessions is frozen
at that level either way. Backfilling would mean picking one of a project's sessions to
speak for it, which is a guess this migration has no standing to make.

Reuses sn_granularity_level_enum, created by the sn_sessions migration, and reuses it
through postgresql.ENUM rather than sa.Enum. That is not a style choice: ``create_type``
is a postgresql.ENUM keyword, and sa.Enum swallows unknown kwargs into **kw and drops it
on the floor — ``sa.Enum(..., create_type=False)`` has no create_type attribute at all,
so create_table would emit a CREATE TYPE for a type that already exists and the upgrade
would fail on deploy. The downgrade leaves the type alone for the same reason it is not
created here: sn_sessions owns it and still uses it.

Creates only the sn_* table. This database is shared with every other Tripod app, so
nothing here alters or drops anything it did not create.

Revision ID: 20260724_0001
Revises: 20260723_0001
Create Date: 2026-07-24 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# Declared once, and through postgresql.ENUM: sa.Enum would drop create_type silently
# (it takes **kw) and emit a CREATE TYPE for a type sn_sessions already created.
_GRANULARITY_ENUM = postgresql.ENUM(
    "small",
    "medium",
    "large",
    name="sn_granularity_level_enum",
    create_type=False,
)

revision: str = "20260724_0001"
down_revision: str | None = "20260723_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sn_project_settings",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("granularity_level", _GRANULARITY_ENUM, nullable=False),
        # Null until the project cuts its first audio: no grid yet, nothing to agree with.
        sa.Column("bead_sec", sa.Float(), nullable=True),
        # Nullable, and SET NULL below: the setting outlives the account that chose it.
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        # SET NULL, never CASCADE: deleting the admin who chose the granularity must not
        # take a project's grid with it. RESTRICT is not the answer either — `users` is
        # shared with every other Tripod app, and a row here must not be what makes
        # deleting a user fail over there.
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        # One decision per project. The whole point of the table.
        sa.PrimaryKeyConstraint("project_id"),
    )


def downgrade() -> None:
    op.drop_table("sn_project_settings")
    # sn_granularity_level_enum is NOT dropped: sn_sessions created it and still uses it.
