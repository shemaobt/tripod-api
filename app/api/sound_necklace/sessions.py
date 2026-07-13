"""Session lifecycle + autosave stub routes."""

from fastapi import APIRouter, status

from app.api.sound_necklace._deps import CurrentUser, not_implemented
from app.models.sound_necklace import (
    AutosaveResponse,
    SessionCreate,
    SessionListResponse,
    SessionStateUpdate,
    SessionSummary,
)

router = APIRouter()


@router.post("/sessions", response_model=SessionSummary, status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionCreate, user: CurrentUser) -> SessionSummary:
    """Create a session from a bucket audio and grid parameters."""
    not_implemented()


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(user: CurrentUser) -> SessionListResponse:
    """List the caller's sessions with status and progress."""
    not_implemented()


@router.get("/sessions/{session_id}", response_model=SessionSummary)
async def get_session(session_id: str, user: CurrentUser) -> SessionSummary:
    """Fetch a single session for resume."""
    not_implemented()


@router.put("/sessions/{session_id}/state", response_model=AutosaveResponse)
async def autosave_session(
    session_id: str, payload: SessionStateUpdate, user: CurrentUser
) -> AutosaveResponse:
    """Autosave the session-state envelope with a version guard."""
    not_implemented()


@router.post("/sessions/{session_id}/complete", response_model=SessionSummary)
async def complete_session(session_id: str, user: CurrentUser) -> SessionSummary:
    """Complete a session (its artifacts are uploaded to the artifacts route)."""
    not_implemented()


@router.post("/sessions/{session_id}/reopen", response_model=SessionSummary)
async def reopen_session(session_id: str, user: CurrentUser) -> SessionSummary:
    """Reopen a completed session."""
    not_implemented()
