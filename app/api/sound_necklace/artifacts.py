"""Artifact download stub route (opaque bytes; upload happens on complete)."""

from fastapi import APIRouter

from app.api.sound_necklace._deps import CurrentUser, not_implemented
from app.models.sound_necklace import ArtifactKind

router = APIRouter()


@router.get("/sessions/{session_id}/artifacts/{kind}")
async def download_artifact(session_id: str, kind: ArtifactKind, user: CurrentUser) -> None:
    """Download one opaque artifact by kind."""
    not_implemented()
