from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.sound_necklace import ConsentType, SnConsent, SnSession


async def record_consent(
    db: AsyncSession, session_id: str, consent_type: ConsentType, confirmed_by: str
) -> SnConsent:
    """Record a consent as evidence of a lawful basis (§12), or re-confirm one.

    Idempotent per (session, type): a second confirmation updates the record rather
    than stacking another one, and names whoever confirmed it this time. Note what that
    means, because it is the record's one weakness: re-confirming REPLACES the previous
    attester and timestamp. The key is idempotent, the value is not.

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

    if consent_type is ConsentType.PIPELINE_USE:
        # Keep the session's boolean from contradicting the record. It is write-only
        # today — no response carries it and the SPA reads its own copy out of the state
        # document — but two columns claiming the same fact must not disagree: a session
        # opened without consent whose consent is recorded afterwards would otherwise sit
        # there reading `false` next to an authoritative record saying granted, and
        # whoever wires the first read of it inherits a lie.
        session = await db.get(SnSession, session_id)
        if session is not None:
            session.pipeline_consent = True

    await db.commit()
    return record
