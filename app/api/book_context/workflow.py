from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.book_context._deps import MM_APP_KEY, mm_access
from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.core.exceptions import AuthorizationError, ConflictError
from app.db.models.auth import User
from app.models.book_context import (
    BCDGenerateRequest,
    BCDGenerationLogResponse,
    BCDResponse,
    CancelGenerationResponse,
)
from app.services import authorization_service
from app.services.book_context.approve_bcd import approve_bcd
from app.services.book_context.cancel_generation import cancel_generation
from app.services.book_context.create_new_version import create_new_version
from app.services.book_context.enrich_bcd_response import enrich_bcd_response
from app.services.book_context.generation.run import run_bcd_generation
from app.services.book_context.list_generation_logs import list_generation_logs
from app.services.book_context.request_revision import request_revision
from app.services.book_context.set_active import set_active_bcd
from app.services.book_context.start_generation import (
    GenerationAlreadyInProgress,
    start_generation,
)

router = APIRouter()


@router.post("/{bcd_id}/approve", response_model=BCDResponse, dependencies=[mm_access])
async def approve_book_context_document(
    bcd_id: str,
    locale: str = Query(default="en"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BCDResponse:
    user_roles = await authorization_service.resolve_user_app_roles(db, user, MM_APP_KEY)
    bcd = await approve_bcd(db, bcd_id, user.id, user_roles, locale=locale)
    return await enrich_bcd_response(db, bcd)


@router.post("/{bcd_id}/set-active", response_model=BCDResponse, dependencies=[mm_access])
async def set_active_version(
    bcd_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BCDResponse:
    role = await authorization_service.resolve_user_app_role(db, user, MM_APP_KEY)
    if role != "admin":
        raise AuthorizationError("Only admins can set the active version.")
    bcd = await set_active_bcd(db, bcd_id)
    return await enrich_bcd_response(db, bcd)


@router.post(
    "/{bcd_id}/cancel-generation",
    response_model=CancelGenerationResponse,
    dependencies=[mm_access],
)
async def cancel_bcd_generation(
    bcd_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CancelGenerationResponse:
    role = await authorization_service.resolve_user_app_role(db, user, MM_APP_KEY)
    if role != "admin":
        raise AuthorizationError("Only admins can cancel generation.")
    book_id = await cancel_generation(db, bcd_id)
    return CancelGenerationResponse(deleted=True, book_id=book_id)


@router.post("/{bcd_id}/request-revision", response_model=BCDResponse, dependencies=[mm_access])
async def request_bcd_revision(
    bcd_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BCDResponse:
    role = await authorization_service.resolve_user_app_role(db, user, MM_APP_KEY)
    bcd = await request_revision(db, bcd_id, user.id, role)
    return await enrich_bcd_response(db, bcd)


@router.post(
    "/{bcd_id}/new-version",
    response_model=BCDResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[mm_access],
)
async def create_new_bcd_version(
    bcd_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BCDResponse:
    bcd = await create_new_version(db, bcd_id, user.id)
    return await enrich_bcd_response(db, bcd)


@router.get(
    "/{bcd_id}/logs",
    response_model=list[BCDGenerationLogResponse],
    dependencies=[mm_access],
)
async def get_generation_logs(
    bcd_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[BCDGenerationLogResponse]:
    logs = await list_generation_logs(db, bcd_id)
    return [BCDGenerationLogResponse.model_validate(log) for log in logs]


@router.post(
    "/{bcd_id}/generate",
    response_model=BCDResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[mm_access],
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
        raise ConflictError("Generation is already in progress.") from err

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
