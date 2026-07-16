from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.sound_necklace import SessionStatus, SnSession


async def reopen_session(db: AsyncSession, session: SnSession) -> SnSession:
    """Put a completed session back in progress. Idempotent."""
    if session.status is not SessionStatus.IN_PROGRESS:
        session.status = SessionStatus.IN_PROGRESS
        session.completed_at = None
        await db.commit()
        await db.refresh(session)
    return session
