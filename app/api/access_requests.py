from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_middleware import get_current_user, require_platform_admin
from app.core.database import get_db
from app.db.models.auth import App, User
from app.models.access_request import (
    AccessRequestCreate,
    AccessRequestResponse,
    AccessRequestReviewRequest,
)
from app.services import access_request_service

router = APIRouter()


def _to_response(request, app_key: str) -> AccessRequestResponse:
    return AccessRequestResponse(
        id=request.id,
        user_id=request.user_id,
        app_key=app_key,
        status=request.status,
        note=request.note,
        requested_at=request.requested_at,
        reviewed_by=request.reviewed_by,
        reviewed_at=request.reviewed_at,
        review_reason=request.review_reason,
    )


@router.post("", response_model=AccessRequestResponse)
async def create_access_request(
    payload: AccessRequestCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AccessRequestResponse:
    request = await access_request_service.create_access_request(
        db, user.id, payload.app_key, payload.note
    )
    return _to_response(request, payload.app_key)


@router.get("/mine", response_model=AccessRequestResponse | None)
async def get_my_access_request(
    app_key: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AccessRequestResponse | None:
    request = await access_request_service.get_user_access_request(db, user.id, app_key)
    if not request:
        return None
    return _to_response(request, app_key)


@router.get("", response_model=list[AccessRequestResponse])
async def list_access_requests(
    app_key: str | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> list[AccessRequestResponse]:
    rows = await access_request_service.list_access_requests(db, app_key, status)
    return [_to_response(req, ak) for req, ak in rows]


@router.patch("/{request_id}/review", response_model=AccessRequestResponse)
async def review_access_request(
    request_id: str,
    payload: AccessRequestReviewRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_platform_admin),
) -> AccessRequestResponse:
    request = await access_request_service.review_access_request(
        db, actor, request_id, payload.status, payload.reason
    )
    # Resolve app_key from app_id
    app_result = await db.execute(select(App).where(App.id == request.app_id))
    app = app_result.scalar_one()
    return _to_response(request, app.app_key)
