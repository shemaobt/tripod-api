"""Session lifecycle + autosave stubs (§7.2/§7.3). Implemented by ENG-260."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.colar._deps import CurrentUser, not_implemented
from app.models.colar import (
    AutosaveResponse,
    CompleteSessionRequest,
    CreateSessionRequest,
    SessionListResponse,
    SessionStatePayload,
    SessionSummary,
)

router = APIRouter()


@router.post("/sessions", response_model=SessionSummary, status_code=status.HTTP_201_CREATED)
async def create_session(payload: CreateSessionRequest, user: CurrentUser) -> SessionSummary:
    """Create a session from a bucket audio + grid params (§8.1)."""
    not_implemented()


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(user: CurrentUser) -> SessionListResponse:
    """List the caller's sessions with status + progress (§7.3)."""
    not_implemented()


@router.get("/sessions/{session_id}", response_model=SessionSummary)
async def get_session(session_id: str, user: CurrentUser) -> SessionSummary:
    """Fetch one session, for resume (§7.3)."""
    not_implemented()


@router.put("/sessions/{session_id}/state", response_model=AutosaveResponse)
async def autosave_session(
    session_id: str, payload: SessionStatePayload, user: CurrentUser
) -> AutosaveResponse:
    """Autosave the session-state envelope with a version guard (§7.3)."""
    not_implemented()


@router.post("/sessions/{session_id}/complete", response_model=SessionSummary)
async def complete_session(
    session_id: str, payload: CompleteSessionRequest, user: CurrentUser
) -> SessionSummary:
    """Complete a session, uploading the opaque artifact triple (§8.8)."""
    not_implemented()


@router.post("/sessions/{session_id}/reopen", response_model=SessionSummary)
async def reopen_session(session_id: str, user: CurrentUser) -> SessionSummary:
    """Reopen a completed session (§7.3)."""
    not_implemented()
