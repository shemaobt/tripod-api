from sqlalchemy.ext.asyncio import AsyncSession

from app.services.oral_collector import acousteme_service


async def audio_signed_url(db: AsyncSession, audio_id: str) -> str:
    """A short-lived signed GET for the audio's own private object.

    The bytes are never proxied through the API. The acousteme service already resolves
    the artifact and signs its private bucket/object with the ambient service account —
    the audio is in a private bucket already, so there is nothing to copy anywhere and
    this is that call.

    What this adds is the caller: the route has passed the project gate before reaching
    here, which is the entire reason the SPA is not pointed at the Oral Collector's own
    acousteme routes, which have no project scoping.
    """
    audio = await acousteme_service.get_audio_url(db, audio_id)
    return audio.download_url
