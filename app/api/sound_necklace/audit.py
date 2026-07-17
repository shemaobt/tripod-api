"""The audit trail: who reached whose voice, and when (§12).

Read-only. The events are written by the services that do the reaching, one explicit call
each — no middleware, which in a monolith six apps share would be a guess about which
routes matter and would not know the project the log is queried by.

Reading it takes ``project_admin`` on top of project membership. A facilitator reading who
reached what is the surveillance §14 forbids, one step removed; and the role alone is not
enough either, or an admin of one project could read another's.
"""

from datetime import datetime

from fastapi import APIRouter, Query

from app.api.projects._deps import assert_project_access
from app.api.sound_necklace._deps import Db, ProjectAdmin
from app.db.models.sound_necklace import AuditEvent, SnAuditEvent
from app.models.sound_necklace import AuditEventResponse, AuditListResponse
from app.services import sound_necklace_service as sn_service
from app.services.sound_necklace.get_lock_status import as_utc

router = APIRouter()


def _event(row: SnAuditEvent) -> AuditEventResponse:
    return AuditEventResponse(
        id=row.id,
        occurred_at=as_utc(row.occurred_at).isoformat(),
        event=row.event,
        user_id=row.user_id,
        session_id=row.session_id,
        resource_ref=row.resource_ref,
    )


@router.get("/projects/{project_id}/audit", response_model=AuditListResponse)
async def list_audit_events(
    project_id: str,
    db: Db,
    user: ProjectAdmin,
    since: datetime | None = Query(None, description="Only events at or after this instant"),
    event: AuditEvent | None = Query(None, description="Only this kind of event"),
    limit: int = Query(100, ge=1, le=500),
) -> AuditListResponse:
    """One project's audit trail, newest first.

    An empty list is an answer — a window in which nothing was reached — not an error.
    """
    await assert_project_access(db, user, project_id)
    rows = await sn_service.list_audit_events(db, project_id, since=since, event=event, limit=limit)
    return AuditListResponse(events=[_event(r) for r in rows])
