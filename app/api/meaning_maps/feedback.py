from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.core.exceptions import AuthorizationError
from app.db.models.auth import User
from app.models.meaning_map import FeedbackCreate, FeedbackResponse, FeedbackUpdate
from app.services import meaning_map_service, notification_service
from app.services.notifications.get_mm_app_id import get_mm_app_id

from app.api.meaning_maps._deps import mm_access, mm_analyst

router = APIRouter()

@router.post(
    "/{map_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[mm_analyst],
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

@router.get("/{map_id}/feedback", response_model=list[FeedbackResponse], dependencies=[mm_access])
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
    dependencies=[mm_access],
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
