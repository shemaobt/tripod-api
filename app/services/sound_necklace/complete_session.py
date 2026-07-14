from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.sound_necklace import SessionStatus, SnSession


async def complete_session(db: AsyncSession, session: SnSession) -> SnSession:
    """Mark a session complete. Idempotent: completing a completed session is a no-op.

    ``current_step`` is deliberately left alone — it records where the state was
    left, and a completed session simply displays as the last station. Reopening
    then lands back on the real one.
    """
    if session.status is not SessionStatus.COMPLETED:
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(session)
    return session
