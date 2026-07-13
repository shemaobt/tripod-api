"""Voice-answer resource stub routes (canonical respostas/... paths)."""

from fastapi import APIRouter, status

from app.api.sound_necklace._deps import CurrentUser, not_implemented
from app.models.sound_necklace import ResourcePresignResponse, ResourceRef

router = APIRouter()


@router.post("/sessions/{session_id}/resources/presign-put", response_model=ResourcePresignResponse)
async def presign_put_resource(
    session_id: str, payload: ResourceRef, user: CurrentUser
) -> ResourcePresignResponse:
    """Presign a PUT for a voice answer at a canonical path."""
    not_implemented()


@router.post("/sessions/{session_id}/resources/complete", response_model=ResourceRef)
async def complete_resource(
    session_id: str, payload: ResourceRef, user: CurrentUser
) -> ResourceRef:
    """Acknowledge a completed voice-answer upload."""
    not_implemented()


@router.post("/sessions/{session_id}/resources/presign-get", response_model=ResourcePresignResponse)
async def presign_get_resource(
    session_id: str, payload: ResourceRef, user: CurrentUser
) -> ResourcePresignResponse:
    """Presign a GET for a stored voice answer."""
    not_implemented()


@router.delete("/sessions/{session_id}/resources", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(session_id: str, payload: ResourceRef, user: CurrentUser) -> None:
    """Delete a voice answer by path."""
    not_implemented()
