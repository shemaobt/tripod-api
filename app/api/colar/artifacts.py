"""Artifact download stub route (opaque bytes; upload happens on complete)."""

from fastapi import APIRouter

from app.api.colar._deps import CurrentUser, not_implemented
from app.models.colar import ArtifactKind

router = APIRouter()


@router.get("/sessions/{session_id}/artifacts/{kind}")
async def download_artifact(session_id: str, kind: ArtifactKind, user: CurrentUser) -> None:
    """Download one opaque artifact by kind."""
    not_implemented()
