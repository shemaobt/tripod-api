from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.sound_necklace import ConsentType, SnConsent


async def record_consent(
    db: AsyncSession, session_id: str, consent_type: ConsentType, confirmed_by: str
) -> SnConsent:
    """Record a consent as evidence of a lawful basis (§12), or re-confirm one.

    Idempotent per (session, type): a second confirmation updates the record rather
    than stacking another one, and names whoever confirmed it this time.

    ``confirmed_at`` is assigned here rather than left to ``onupdate=func.now()``. A
    re-confirmation of an unchanged record changes no other column, and the ORM emits
    no UPDATE at all when nothing is dirty — the timestamp would silently stay at the
    first confirmation. The one thing this record must never get wrong is when it was
    confirmed.

    The commit is what makes this composable from ``create_session``: called with a
    session still pending, it writes the session, its state and the consent in one
    transaction, so a session can never be stored claiming a consent that was not
    recorded alongside it.
    """
    record = await db.get(SnConsent, (session_id, consent_type))
    if record is None:
        record = SnConsent(session_id=session_id, type=consent_type)
        db.add(record)
    record.confirmed_by = confirmed_by
    record.confirmed_at = datetime.now(UTC)
    await db.commit()
    return record
