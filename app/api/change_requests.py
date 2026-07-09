from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_middleware import get_current_user, require_platform_admin
from app.core.database import get_db
from app.db.models.auth import User
from app.db.models.change_request import ChangeRequest
from app.models.change_request import (
    ChangeRequestCreate,
    ChangeRequestResponse,
    ChangeRequestReview,
)
from app.services import change_request_service

router = APIRouter()


def _to_response(request: ChangeRequest, requester: User) -> ChangeRequestResponse:
    return ChangeRequestResponse(
        id=request.id,
        kind=request.kind,
        requester_user_id=request.requester_user_id,
        requester_display_name=requester.display_name,
        requester_email=requester.email,
        status=request.status,
        name=request.name,
        code=request.code,
        description=request.description,
        language_id=request.language_id,
        new_language_name=request.new_language_name,
        new_language_code=request.new_language_code,
        grant_manager_access=request.grant_manager_access,
        reviewed_by=request.reviewed_by,
        reviewed_at=request.reviewed_at,
        review_reason=request.review_reason,
        created_entity_id=request.created_entity_id,
        requested_at=request.requested_at,
    )


@router.post("", response_model=ChangeRequestResponse, status_code=201)
async def create_change_request(
    payload: ChangeRequestCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChangeRequestResponse:
    request = await change_request_service.create_change_request(db, user.id, payload)
    return _to_response(request, user)


@router.get("/mine", response_model=list[ChangeRequestResponse])
async def list_my_change_requests(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ChangeRequestResponse]:
    rows = await change_request_service.list_my_change_requests(db, user.id)
    return [_to_response(request, requester) for request, requester in rows]


@router.get("", response_model=list[ChangeRequestResponse])
async def list_change_requests(
    kind: str | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> list[ChangeRequestResponse]:
    rows = await change_request_service.list_change_requests(db, kind, status)
    return [_to_response(request, requester) for request, requester in rows]


@router.patch("/{request_id}/review", response_model=ChangeRequestResponse)
async def review_change_request(
    request_id: str,
    payload: ChangeRequestReview,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_platform_admin),
) -> ChangeRequestResponse:
    request, requester = await change_request_service.review_change_request(
        db, actor, request_id, payload.status, payload.reason, payload.grant_manager_access
    )
    return _to_response(request, requester)
