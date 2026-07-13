"""Advisory single-editor lock stub routes."""

from fastapi import APIRouter, status

from app.api.colar._deps import CurrentUser, not_implemented
from app.models.colar import LockStatusResponse

router = APIRouter()


@router.put("/sessions/{session_id}/lock", response_model=LockStatusResponse)
async def acquire_lock(session_id: str, user: CurrentUser) -> LockStatusResponse:
    """Acquire or renew the advisory editor lock."""
    not_implemented()


@router.get("/sessions/{session_id}/lock", response_model=LockStatusResponse)
async def lock_status(session_id: str, user: CurrentUser) -> LockStatusResponse:
    """Report the current lock holder and expiry."""
    not_implemented()


@router.delete("/sessions/{session_id}/lock", status_code=status.HTTP_204_NO_CONTENT)
async def release_lock(session_id: str, user: CurrentUser) -> None:
    """Release the advisory lock."""
    not_implemented()
