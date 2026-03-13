from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.db.models.auth import User
from app.models.book_context import BCDFeedbackCreate, BCDFeedbackResponse
from app.services.book_context.add_feedback import add_feedback
from app.services.book_context.list_feedback import list_feedback
from app.services.book_context.resolve_feedback import resolve_feedback

from app.api.book_context._deps import mm_access

router = APIRouter()

@router.post(
    "/{bcd_id}/feedback",
    response_model=BCDFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[mm_access],
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
    dependencies=[mm_access],
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
    dependencies=[mm_access],
)
async def resolve_bcd_feedback(
    bcd_id: str,
    feedback_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BCDFeedbackResponse:
    fb = await resolve_feedback(db, bcd_id, feedback_id)
    return BCDFeedbackResponse.model_validate(fb)
