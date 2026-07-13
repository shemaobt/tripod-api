"""Advisory single-editor lock stubs (§7.3/O4). Implemented by ENG-260."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.colar._deps import CurrentUser, not_implemented
from app.models.colar import LockStatus

router = APIRouter()


@router.put("/sessions/{session_id}/lock", response_model=LockStatus)
async def acquire_lock(session_id: str, user: CurrentUser) -> LockStatus:
    """Acquire or renew the advisory editor lock (§7.3/O4)."""
    not_implemented()


@router.get("/sessions/{session_id}/lock", response_model=LockStatus)
async def lock_status(session_id: str, user: CurrentUser) -> LockStatus:
    """Report the current lock holder + expiry (§7.3/O4)."""
    not_implemented()


@router.delete(
    "/sessions/{session_id}/lock",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def release_lock(session_id: str, user: CurrentUser) -> None:
    """Release the advisory lock (§7.3/O4)."""
    not_implemented()
