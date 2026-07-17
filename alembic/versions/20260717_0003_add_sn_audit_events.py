"""add sn_audit_events

Who reached whose voice, and when (§12) — until now this existed only as structlog lines
that nothing could query. The events are written by the services that do the reaching, in
the same transaction, so there is never a signed URL issued without a row to say so.

Append-only by nature: nothing updates a row here, because an event is a thing that
happened. Both foreign keys to identity are SET NULL rather than CASCADE — deleting a user
must not erase the record of what that account reached, which is the one question this
table exists to answer and is asked most exactly when the account is gone.

Creates only the sn_* table and its enum type. This database is shared with every other
Tripod app, so nothing here alters or drops anything it did not create.

Revision ID: 20260717_0003
Revises: 20260717_0002
Create Date: 2026-07-17 03:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "20260717_0003"
down_revision: str | None = "20260717_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sn_audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column(
            "event",
            sa.Enum(
                "audio_url_issued",
                "artifact_uploaded",
                "artifact_url_issued",
                "voice_url_issued",
                "session_completed",
                "session_reopened",
                "consent_recorded",
                name="sn_audit_event_enum",
            ),
            nullable=False,
        ),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        # 255 with room to spare: the longest ref is a voice answer's respostas/… path,
        # bounded at 93 by its allowlist. The storage keys are NOT stored here — an
        # artifact's is content-addressed and moves under a re-upload, and the audio's
        # object name lives in an unbounded Text column upstream.
        sa.Column("resource_ref", sa.String(length=255), nullable=False),
        # 45 = the longest IPv6 form. Nothing writes it: behind Cloud Run's proxy there is
        # no address this API can honestly attribute to the caller. The column ships now
        # because adding it later is a migration on a shared production database.
        sa.Column("ip", sa.String(length=45), nullable=True),
        # SET NULL on both: an audit row must outlive the account it names and the session
        # it happened in. Under CASCADE, deleting the user would erase the evidence of what
        # they reached — the exact records an investigation wants.
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["sn_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # The three shapes of the only query there is: scoped to a project, optionally
    # narrowed by kind, windowed by time.
    op.create_index("ix_sn_audit_events_project_id", "sn_audit_events", ["project_id"])
    op.create_index("ix_sn_audit_events_occurred_at", "sn_audit_events", ["occurred_at"])
    op.create_index("ix_sn_audit_events_event", "sn_audit_events", ["event"])
    op.create_index("ix_sn_audit_events_user_id", "sn_audit_events", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_sn_audit_events_user_id", table_name="sn_audit_events")
    op.drop_index("ix_sn_audit_events_event", table_name="sn_audit_events")
    op.drop_index("ix_sn_audit_events_occurred_at", table_name="sn_audit_events")
    op.drop_index("ix_sn_audit_events_project_id", table_name="sn_audit_events")
    op.drop_table("sn_audit_events")

    # drop_table does not drop the TYPE create_table implicitly created, and leaving it
    # behind makes the next upgrade fail on a type that already exists.
    bind = op.get_bind()
    bind.execute(sa.text("DROP TYPE IF EXISTS sn_audit_event_enum"))
