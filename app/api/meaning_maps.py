import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_app_access, require_role
from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.core.exceptions import AuthorizationError
from app.core.qdrant import get_qdrant_client
from app.db.models.auth import User
from app.db.models.meaning_map import MeaningMap as MeaningMapModel
from app.db.models.meaning_map import MeaningMapStatus
from app.models.meaning_map import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackUpdate,
    MeaningMapGenerateRequest,
    MeaningMapListResponse,
    MeaningMapResponse,
    MeaningMapStatusUpdate,
    MeaningMapUpdateData,
)
from app.services import meaning_map_service, notification_service
from app.services.book_context.compute_entry_brief import compute_entry_brief
from app.services.meaning_map.generator import (
    GenerationError,
)
from app.services.meaning_map.generator import (
    generate_meaning_map as run_generation,
)
from app.services.notifications.get_mm_app_id import get_mm_app_id

logger = logging.getLogger(__name__)

router = APIRouter()
_mm_access = require_app_access("meaning-map-generator")
_mm_analyst = require_role("meaning-map-generator", "analyst")

async def _enrich_response(db: AsyncSession, mm: MeaningMapModel) -> MeaningMapResponse:

    pericope, book = await meaning_map_service.get_pericope_with_book(db, mm.pericope_id)
    resp = MeaningMapResponse.model_validate(mm)
    resp.book_id = book.id
    resp.book_name = book.name
    resp.pericope_reference = pericope.reference
    return resp

@router.get("", response_model=list[MeaningMapListResponse], dependencies=[_mm_access])
async def list_meaning_maps(
    book_id: str | None = Query(default=None),
    chapter: int | None = Query(default=None),
    map_status: str | None = Query(default=None, alias="status"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MeaningMapListResponse]:
    maps = await meaning_map_service.list_meaning_maps(
        db, book_id=book_id, chapter=chapter, status=map_status
    )
    return [MeaningMapListResponse.model_validate(m) for m in maps]

@router.get("/{map_id}", response_model=MeaningMapResponse, dependencies=[_mm_access])
async def get_meaning_map(
    map_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeaningMapResponse:
    mm = await meaning_map_service.get_meaning_map_or_404(db, map_id)
    return await _enrich_response(db, mm)

@router.put("/{map_id}", response_model=MeaningMapResponse, dependencies=[_mm_analyst])
async def update_meaning_map(
    map_id: str,
    payload: MeaningMapUpdateData,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeaningMapResponse:
    mm, book = await meaning_map_service.get_map_with_book(db, map_id)
    meaning_map_service.ensure_ot(book)
    mm = await meaning_map_service.update_meaning_map_data(db, mm, payload.data, user.id)
    return await _enrich_response(db, mm)

@router.patch("/{map_id}/status", response_model=MeaningMapResponse, dependencies=[_mm_analyst])
async def update_status(
    map_id: str,
    payload: MeaningMapStatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeaningMapResponse:
    mm = await meaning_map_service.get_meaning_map_or_404(db, map_id)
    mm = await meaning_map_service.transition_status(db, mm, payload.status, user.id)
    return await _enrich_response(db, mm)

@router.post("/{map_id}/lock", response_model=MeaningMapResponse, dependencies=[_mm_analyst])
async def lock_map(
    map_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeaningMapResponse:
    mm = await meaning_map_service.get_meaning_map_or_404(db, map_id)
    mm = await meaning_map_service.lock_map(db, mm, user.id)
    return await _enrich_response(db, mm)

@router.post("/{map_id}/unlock", response_model=MeaningMapResponse, dependencies=[_mm_analyst])
async def unlock_map(
    map_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeaningMapResponse:
    mm = await meaning_map_service.get_meaning_map_or_404(db, map_id)
    mm = await meaning_map_service.unlock_map(db, mm, user.id, is_admin=user.is_platform_admin)
    return await _enrich_response(db, mm)

@router.delete("/{map_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_mm_analyst])
async def delete_meaning_map(
    map_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    mm = await meaning_map_service.get_meaning_map_or_404(db, map_id)
    await meaning_map_service.delete_meaning_map(db, mm, user.id)

@router.post(
    "/generate",
    response_model=MeaningMapResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_mm_analyst],
)
async def generate_meaning_map(
    payload: MeaningMapGenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeaningMapResponse:
    pericope, book = await meaning_map_service.get_pericope_with_book(db, payload.pericope_id)
    meaning_map_service.ensure_ot(book)

    bcd_version: int | None = None
    entry_brief_data: dict | None = None
    try:
        entry_brief = await compute_entry_brief(db, payload.pericope_id)
        bcd_version = entry_brief.bcd_version
        entry_brief_data = entry_brief.model_dump()
    except Exception:
        logger.warning(
            "Entry brief computation failed for pericope %s — generating without Book Context",
            payload.pericope_id,
            exc_info=True,
        )

    try:
        qdrant = get_qdrant_client()
    except RuntimeError as exc:
        raise GenerationError("RAG service is not available. Contact an administrator.") from exc
    try:
        generated_data = await run_generation(
            pericope.reference,
            qdrant_client=qdrant,
            entry_brief=entry_brief_data,
        )
    except GenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    mm = await meaning_map_service.create_meaning_map(
        db,
        pericope_id=payload.pericope_id,
        analyst_id=user.id,
        data=generated_data,
        bcd_version_at_creation=bcd_version,
    )
    return await _enrich_response(db, mm)

@router.get("/{map_id}/export/json", dependencies=[_mm_access])
async def export_json(
    map_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    mm = await meaning_map_service.get_meaning_map_or_404(db, map_id)
    if mm.status != MeaningMapStatus.APPROVED:
        raise AuthorizationError("Only approved meaning maps can be exported")
    content = meaning_map_service.export_json(mm)
    return PlainTextResponse(content, media_type="application/json")

@router.get("/{map_id}/export/prose", dependencies=[_mm_access])
async def export_prose(
    map_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    mm = await meaning_map_service.get_meaning_map_or_404(db, map_id)
    if mm.status != MeaningMapStatus.APPROVED:
        raise AuthorizationError("Only approved meaning maps can be exported")
    content = meaning_map_service.export_prose(mm)
    return PlainTextResponse(content, media_type="text/markdown")

@router.post(
    "/{map_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_mm_analyst],
)
async def add_feedback(
    map_id: str,
    payload: FeedbackCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    mm = await meaning_map_service.get_meaning_map_or_404(db, map_id)
    if mm.status != "cross_check":
        raise AuthorizationError("Feedback can only be added during cross-check phase")
    if mm.locked_by and mm.locked_by != user.id:
        raise AuthorizationError("Only the cross-checker can add feedback")
    fb = await meaning_map_service.add_feedback(
        db, map_id, payload.section_key, user.id, payload.content
    )
    resp = FeedbackResponse.model_validate(fb)
    resp.author_name = user.display_name
    return resp

@router.get("/{map_id}/feedback", response_model=list[FeedbackResponse], dependencies=[_mm_access])
async def list_feedback(
    map_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FeedbackResponse]:
    items = await meaning_map_service.list_feedback(db, map_id)
    return [FeedbackResponse.model_validate(fb) for fb in items]

@router.patch(
    "/{map_id}/feedback/{feedback_id}",
    response_model=FeedbackResponse,
    dependencies=[_mm_access],
)
async def resolve_feedback(
    map_id: str,
    feedback_id: str,
    payload: FeedbackUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    fb = await meaning_map_service.resolve_feedback(db, map_id, feedback_id)

    if fb.author_id != user.id:
        mm = await meaning_map_service.get_meaning_map_or_404(db, map_id)
        pericope, _ = await meaning_map_service.get_pericope_with_book(db, mm.pericope_id)
        app_id = await get_mm_app_id(db)
        await notification_service.create_notification(
            db,
            user_id=fb.author_id,
            app_id=app_id,
            event_type="feedback_resolved",
            title="Your feedback was resolved",
            body=f"Your feedback on the meaning map for {pericope.reference} was resolved.",
            actor_id=user.id,
            related_map_id=map_id,
            pericope_reference=pericope.reference,
        )

    return FeedbackResponse.model_validate(fb)
