from fastapi import APIRouter

from app.api.annotation_studio._deps import CurrentUser
from app.services.annotation_studio import storage

router = APIRouter()


@router.get("/audio/url")
async def audio_url(key: str, _: CurrentUser) -> dict[str, str]:
    """A short-lived signed GET URL for client-side playback of a stored object."""
    return {"url": storage.presign_get(key)}
