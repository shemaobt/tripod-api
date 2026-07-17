from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.sound_necklace import AuditEvent, SnAuditEvent


async def record_audit_event(
    db: AsyncSession,
    *,
    event: AuditEvent,
    user_id: str,
    project_id: str,
    resource_ref: str,
    session_id: str | None = None,
) -> SnAuditEvent:
    """Record one reach for protected material (§12).

    Added to the caller's transaction and deliberately NOT committed here: the audit row
    and the operation it records have to land together, so the caller's own commit is what
    writes both. A commit of its own would let an event describe an operation that then
    rolled back.

    No try/except either. If this write fails the operation must fail with it — the
    alternative is a signed URL handed out with no record of who got it, which is the one
    outcome the log exists to prevent. There is no "audit down, operation up" case worth
    engineering for: this is the same session and the same database the route already read
    from, so a database that cannot take this row already failed the route upstream.

    ``ip`` is not a parameter. Behind Cloud Run's proxy the only addresses available are
    the proxy's own and a forgeable ``X-Forwarded-For``, and a number that reads like the
    caller's address but is not is worse in an evidence log than an absent one.
    """
    row = SnAuditEvent(
        occurred_at=datetime.now(UTC),
        user_id=user_id,
        event=event,
        session_id=session_id,
        project_id=project_id,
        resource_ref=resource_ref,
    )
    db.add(row)
    return row
