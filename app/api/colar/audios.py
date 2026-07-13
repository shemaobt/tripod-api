"""Project audio bucket stubs (§7.4). Implemented by ENG-261 over PR #100.

The acousteme envelope is served OPAQUE here (§15.2 O8); ENG-261 reconciles the
concrete shape (tripod-api ``AcoustemeStreamResponse``). The signed-URL route is
the audit point that ENG-266 hooks.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.colar._deps import CurrentUser, not_implemented
from app.models.colar import AudioUrlResponse, BucketListResponse

router = APIRouter()


@router.get("/projects/{project_id}/audios", response_model=BucketListResponse)
async def list_project_audios(project_id: str, user: CurrentUser) -> BucketListResponse:
    """List a project's story audios with their acousteme envelope + consent flag (§7.4)."""
    not_implemented()


@router.get("/audios/{audio_id}/url", response_model=AudioUrlResponse)
async def audio_signed_url(audio_id: str, user: CurrentUser) -> AudioUrlResponse:
    """Mint a short-TTL signed GET for audio bytes — the audit point (§7.4/§12)."""
    not_implemented()
