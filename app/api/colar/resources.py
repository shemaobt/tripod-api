"""Voice-answer resource stubs by canonical ``respostas/...`` path (§10.4).

Bytes are WebM/Opus and travel opaque, out of band; only the path is modeled
here. Implemented by the voice-resource issue.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.colar._deps import CurrentUser, not_implemented
from app.models.colar import PresignResponse, ResourceRef

router = APIRouter()


@router.post("/sessions/{session_id}/resources/presign-put", response_model=PresignResponse)
async def presign_put_resource(
    session_id: str, payload: ResourceRef, user: CurrentUser
) -> PresignResponse:
    """Presign a PUT for a voice answer at a canonical path (§10.4)."""
    not_implemented()


@router.post("/sessions/{session_id}/resources/complete", response_model=ResourceRef)
async def complete_resource(
    session_id: str, payload: ResourceRef, user: CurrentUser
) -> ResourceRef:
    """Acknowledge a completed voice-answer upload (§10.4)."""
    not_implemented()


@router.post("/sessions/{session_id}/resources/presign-get", response_model=PresignResponse)
async def presign_get_resource(
    session_id: str, payload: ResourceRef, user: CurrentUser
) -> PresignResponse:
    """Presign a GET for a stored voice answer (§10.4)."""
    not_implemented()


@router.delete(
    "/sessions/{session_id}/resources",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_resource(session_id: str, payload: ResourceRef, user: CurrentUser) -> None:
    """Delete a voice answer by path (§10.4)."""
    not_implemented()
