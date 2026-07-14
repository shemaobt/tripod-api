from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import User
from app.db.models.sound_necklace import SnSession, SnSessionState
from app.models.sound_necklace import SessionCreate


async def create_session(db: AsyncSession, user: User, payload: SessionCreate) -> SnSession:
    """Open a session on a bucket audio, at the first station and with no state yet.

    The state row is created empty alongside the session so that every autosave is a
    plain conditional UPDATE — there is no insert-or-update race on the first save.
    """
    session = SnSession(
        project_id=payload.project_id,
        created_by=user.id,
        audio_ref=payload.audio_id,
        story_name=payload.story_name,
        slug=payload.story_slug,
        manifest_id=payload.manifest_id,
        granularity_level=payload.granularity_level,
        bead_sec=payload.bead_sec,
        pipeline_consent=payload.pipeline_consent,
    )
    db.add(session)
    await db.flush()
    db.add(SnSessionState(session_id=session.id))
    await db.commit()
    await db.refresh(session)
    return session
