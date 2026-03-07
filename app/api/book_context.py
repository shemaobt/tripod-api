from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_app_access
from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.db.models.auth import User
from app.models.book_context import (
    BCDApprovalStatusResponse,
    BCDCreateRequest,
    BCDFeedbackCreate,
    BCDFeedbackResponse,
    BCDGenerateRequest,
    BCDGenerationLogResponse,
    BCDListResponse,
    BCDResponse,
    BCDSectionUpdateRequest,
    PassageEntryBriefResponse,
)
from app.services import authorization_service
from app.services.book_context.add_feedback import add_feedback
from app.services.book_context.approve_bcd import approve_bcd
from app.services.book_context.cancel_generation import cancel_generation
from app.services.book_context.check_stale import check_bcd_staleness
from app.services.book_context.compute_entry_brief import compute_entry_brief
from app.services.book_context.create_bcd import create_bcd
from app.services.book_context.create_new_version import create_new_version
from app.services.book_context.generation.run import run_bcd_generation
from app.services.book_context.get_approval_status import get_approval_status
from app.services.book_context.get_bcd import get_bcd_or_404
from app.services.book_context.list_bcds import list_bcds
from app.services.book_context.list_feedback import list_feedback
from app.services.book_context.list_generation_logs import list_generation_logs
from app.services.book_context.request_revision import request_revision
from app.services.book_context.resolve_feedback import resolve_feedback
from app.services.book_context.set_active import set_active_bcd
from app.services.book_context.start_generation import (
    GenerationAlreadyInProgress,
    start_generation,
)
from app.services.book_context.update_section import update_section
from app.services.book_context.validate_against_brief import validate_map_against_brief

router = APIRouter()
_mm_access = require_app_access("meaning-map-generator")

MM_APP_KEY = "meaning-map-generator"


async def _resolve_user_role(db: AsyncSession, user: User) -> str:
    """Return the highest-priority single role for permission checks."""
    if user.is_platform_admin:
        return "admin"
    roles = await authorization_service.list_roles(db, user.id, MM_APP_KEY)
    role_keys = [r[1] for r in roles]
    if "admin" in role_keys:
        return "admin"
    if "facilitator" in role_keys:
        return "facilitator"
    if "analyst" in role_keys:
        return "analyst"
    return "viewer"


async def _resolve_user_roles(db: AsyncSession, user: User) -> list[str]:
    """Return all role keys the user holds for the MM app."""
    if user.is_platform_admin:
        return ["admin"]
    roles = await authorization_service.list_roles(db, user.id, MM_APP_KEY)
    return [r[1] for r in roles] or ["viewer"]


@router.get("", response_model=list[BCDListResponse], dependencies=[_mm_access])
async def list_book_context_documents(
    book_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[BCDListResponse]:
    items = await list_bcds(db, book_id=book_id)
    return [BCDListResponse.model_validate(bcd) for bcd in items]


@router.post(
    "/{book_id}",
    response_model=BCDResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_mm_access],
)
async def create_book_context_document(
    book_id: str,
    payload: BCDCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BCDResponse:
    bcd = await create_bcd(
        db,
        book_id,
        user.id,
        payload.genre,
        section_label=payload.section_label,
        section_range_start=payload.section_range_start,
        section_range_end=payload.section_range_end,
    )
    return BCDResponse.model_validate(bcd)


@router.get(
    "/entry-brief/{pericope_id}",
    response_model=PassageEntryBriefResponse,
    dependencies=[_mm_access],
)
async def get_entry_brief(
    pericope_id: str,
    db: AsyncSession = Depends(get_db),
) -> PassageEntryBriefResponse:
    return await compute_entry_brief(db, pericope_id)


@router.get(
    "/staleness-check/{meaning_map_id}",
    dependencies=[_mm_access],
)
async def check_staleness(
    meaning_map_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.services.meaning_map.get_meaning_map_or_404 import get_meaning_map_or_404

    mm = await get_meaning_map_or_404(db, meaning_map_id)
    return await check_bcd_staleness(db, mm)


@router.get(
    "/validate/{meaning_map_id}",
    dependencies=[_mm_access],
)
async def validate_meaning_map(
    meaning_map_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    from app.services.meaning_map.get_meaning_map_or_404 import get_meaning_map_or_404

    mm = await get_meaning_map_or_404(db, meaning_map_id)
    return await validate_map_against_brief(db, mm)


@router.get("/{bcd_id}", response_model=BCDResponse, dependencies=[_mm_access])
async def get_book_context_document(
    bcd_id: str,
    db: AsyncSession = Depends(get_db),
) -> BCDResponse:
    bcd = await get_bcd_or_404(db, bcd_id)
    return BCDResponse.model_validate(bcd)


@router.get(
    "/{bcd_id}/approval-status",
    response_model=BCDApprovalStatusResponse,
    dependencies=[_mm_access],
)
async def get_bcd_approval_status(
    bcd_id: str,
    db: AsyncSession = Depends(get_db),
) -> BCDApprovalStatusResponse:
    status = await get_approval_status(db, bcd_id)
    return BCDApprovalStatusResponse(**status)


@router.patch(
    "/{bcd_id}/sections/{section_key}",
    response_model=BCDResponse,
    dependencies=[_mm_access],
)
async def update_bcd_section(
    bcd_id: str,
    section_key: str,
    payload: BCDSectionUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BCDResponse:
    bcd = await update_section(db, bcd_id, section_key, payload.data)
    return BCDResponse.model_validate(bcd)


@router.post("/{bcd_id}/approve", response_model=BCDResponse, dependencies=[_mm_access])
async def approve_book_context_document(
    bcd_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BCDResponse:
    user_roles = await _resolve_user_roles(db, user)
    bcd = await approve_bcd(db, bcd_id, user.id, user_roles)
    return BCDResponse.model_validate(bcd)


@router.post("/{bcd_id}/set-active", response_model=BCDResponse, dependencies=[_mm_access])
async def set_active_version(
    bcd_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BCDResponse:
    role = await _resolve_user_role(db, user)
    if role not in ("admin", "facilitator"):
        raise HTTPException(
            status_code=403,
            detail="Only admins and facilitators can set the active version.",
        )
    bcd = await set_active_bcd(db, bcd_id)
    return BCDResponse.model_validate(bcd)


@router.post("/{bcd_id}/cancel-generation", dependencies=[_mm_access])
async def cancel_bcd_generation(
    bcd_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    role = await _resolve_user_role(db, user)
    if role not in ("admin", "facilitator"):
        raise HTTPException(
            status_code=403,
            detail="Only admins and facilitators can cancel generation.",
        )
    book_id = await cancel_generation(db, bcd_id)
    return {"deleted": True, "book_id": book_id}


@router.post("/{bcd_id}/request-revision", response_model=BCDResponse, dependencies=[_mm_access])
async def request_bcd_revision(
    bcd_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BCDResponse:
    role = await _resolve_user_role(db, user)
    bcd = await request_revision(db, bcd_id, user.id, role)
    return BCDResponse.model_validate(bcd)


@router.post(
    "/{bcd_id}/new-version",
    response_model=BCDResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_mm_access],
)
async def create_new_bcd_version(
    bcd_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BCDResponse:
    bcd = await create_new_version(db, bcd_id, user.id)
    return BCDResponse.model_validate(bcd)


@router.get(
    "/{bcd_id}/logs",
    response_model=list[BCDGenerationLogResponse],
    dependencies=[_mm_access],
)
async def get_generation_logs(
    bcd_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[BCDGenerationLogResponse]:
    logs = await list_generation_logs(db, bcd_id)
    return [BCDGenerationLogResponse.model_validate(log) for log in logs]


@router.post(
    "/{bcd_id}/feedback",
    response_model=BCDFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_mm_access],
)
async def add_bcd_feedback(
    bcd_id: str,
    payload: BCDFeedbackCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BCDFeedbackResponse:
    fb = await add_feedback(db, bcd_id, payload.section_key, user.id, payload.content)
    return BCDFeedbackResponse.model_validate(fb)


@router.get(
    "/{bcd_id}/feedback",
    response_model=list[BCDFeedbackResponse],
    dependencies=[_mm_access],
)
async def list_bcd_feedback(
    bcd_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[BCDFeedbackResponse]:
    items = await list_feedback(db, bcd_id)
    return [BCDFeedbackResponse.model_validate(fb) for fb in items]


@router.patch(
    "/{bcd_id}/feedback/{feedback_id}",
    response_model=BCDFeedbackResponse,
    dependencies=[_mm_access],
)
async def resolve_bcd_feedback(
    bcd_id: str,
    feedback_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BCDFeedbackResponse:
    fb = await resolve_feedback(db, bcd_id, feedback_id)
    return BCDFeedbackResponse.model_validate(fb)


@router.post(
    "/{bcd_id}/generate",
    response_model=BCDResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[_mm_access],
)
async def generate_bcd(
    bcd_id: str,
    background_tasks: BackgroundTasks,
    payload: BCDGenerateRequest | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BCDResponse:
    feedback = payload.feedback if payload else None
    try:
        target = await start_generation(db, bcd_id, user.id, user_feedback=feedback)
    except GenerationAlreadyInProgress as err:
        raise HTTPException(status_code=409, detail="Generation is already in progress.") from err

    new_bcd_id = target.target_bcd.id
    user_feedback = target.user_feedback

    async def _run_generation() -> None:
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as gen_db:
            try:
                await run_bcd_generation(
                    gen_db,
                    new_bcd_id,
                    book_name=target.book_name,
                    genre=target.genre,
                    chapter_count=target.chapter_count,
                    user_feedback=user_feedback,
                )
            except Exception:
                import logging

                logging.getLogger(__name__).exception("BCD generation failed for %s", new_bcd_id)

    background_tasks.add_task(_run_generation)
    return BCDResponse.model_validate(target.target_bcd)
