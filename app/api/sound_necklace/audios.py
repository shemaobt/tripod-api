"""Project audio bucket stub routes."""

from fastapi import APIRouter

from app.api.sound_necklace._deps import CurrentUser, not_implemented
from app.models.sound_necklace import AudioUrlResponse, BucketAudioListResponse

router = APIRouter()


@router.get("/projects/{project_id}/audios", response_model=BucketAudioListResponse)
async def list_project_audios(project_id: str, user: CurrentUser) -> BucketAudioListResponse:
    """List a project's story audios with their acousteme envelope and consent flag."""
    not_implemented()


@router.get("/audios/{audio_id}/url", response_model=AudioUrlResponse)
async def audio_signed_url(audio_id: str, user: CurrentUser) -> AudioUrlResponse:
    """Mint a short-lived signed GET URL for audio playback."""
    not_implemented()
