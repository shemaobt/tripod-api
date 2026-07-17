"""Consent records — the queryable evidence of a lawful basis (§12 / O6).

The record is the authority; ``sn_sessions.pipeline_consent`` is the convenience copy.
Two routes, and neither takes the client's word for anything but WHICH consent: the
confirmer is the authenticated caller and the timestamp is the server's.

Not fenced by the editor lock, deliberately. The lock guards writes that overwrite each
other; a consent is idempotent per (session, type), so a second facilitator confirming
one cannot destroy the first's work.
"""

from fastapi import APIRouter, status

from app.api.projects._deps import assert_project_access
from app.api.sound_necklace._deps import CurrentUser, Db
from app.db.models.sound_necklace import SnConsent
from app.models.sound_necklace import ConsentCreate, ConsentListResponse, ConsentResponse
from app.services import sound_necklace_service as sn_service

router = APIRouter()


def _record(consent: SnConsent) -> ConsentResponse:
    return ConsentResponse(
        type=consent.type,
        confirmed_by=consent.confirmed_by,
        confirmed_at=consent.confirmed_at.isoformat(),
        oral_recording_path=consent.oral_recording_path,
    )


@router.post(
    "/sessions/{session_id}/consent",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_consent(
    session_id: str, payload: ConsentCreate, db: Db, user: CurrentUser
) -> ConsentResponse:
    """Record a consent, or re-confirm one that is already held.

    Idempotent per (session, type): re-confirming updates the record and its timestamp
    rather than opening a second one. 201 either way — the record exists as stated.
    """
    session = await sn_service.get_session(db, session_id)
    await assert_project_access(db, user, session.project_id)

    return _record(await sn_service.record_consent(db, session_id, payload.type, user.id))


@router.get("/sessions/{session_id}/consent", response_model=ConsentListResponse)
async def list_consents(session_id: str, db: Db, user: CurrentUser) -> ConsentListResponse:
    """The consents held for a session. An empty list means none were given."""
    session = await sn_service.get_session(db, session_id)
    await assert_project_access(db, user, session.project_id)

    return ConsentListResponse(
        consents=[_record(c) for c in await sn_service.list_consents(db, session_id)]
    )
