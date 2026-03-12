from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.db.models.auth import User
from app.models.oc_recording import (
    CleaningStatusResponse,
    RecordingCreate,
    RecordingResponse,
    RecordingUpdate,
    SplitRequest,
    SplitResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services.oral_collector import cleaning_service, recording_service, split_service

recordings_router = APIRouter()


# ---------------------------------------------------------------------------
# Recording CRUD  (prefix: /api/oc/recordings)
# ---------------------------------------------------------------------------


@recordings_router.get("", response_model=list[RecordingResponse])
async def list_recordings(
    project_id: str = Query(..., description="Filter by project"),
    genre_id: str | None = Query(None),
    subcategory_id: str | None = Query(None),
    upload_status: str | None = Query(None),
    cleaning_status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[RecordingResponse]:
    """List recordings for a project with optional filters and pagination."""
    recordings = await recording_service.list_recordings(
        db,
        project_id,
        genre_id=genre_id,
        subcategory_id=subcategory_id,
        upload_status=upload_status,
        cleaning_status=cleaning_status,
        offset=offset,
        limit=limit,
    )
    return [RecordingResponse.model_validate(r) for r in recordings]


@recordings_router.get("/{recording_id}", response_model=RecordingResponse)
async def get_recording(
    recording_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecordingResponse:
    """Get a single recording by ID."""
    recording = await recording_service.get_recording(db, recording_id)
    return RecordingResponse.model_validate(recording)


@recordings_router.post(
    "",
    response_model=RecordingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recording(
    payload: RecordingCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecordingResponse:
    """Create a new recording entry."""
    recording = await recording_service.create_recording(db, payload, user.id)
    return RecordingResponse.model_validate(recording)


@recordings_router.patch("/{recording_id}", response_model=RecordingResponse)
async def update_recording(
    recording_id: str,
    payload: RecordingUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecordingResponse:
    """Update a recording. Restricted to recording owner or project manager."""
    existing = await recording_service.get_recording(db, recording_id)
    await recording_service.check_recording_access(db, existing, user.id)
    recording = await recording_service.update_recording(db, recording_id, payload)
    return RecordingResponse.model_validate(recording)


@recordings_router.delete("/{recording_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recording(
    recording_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a recording. Restricted to recording owner or project manager."""
    existing = await recording_service.get_recording(db, recording_id)
    await recording_service.check_recording_access(db, existing, user.id)
    await recording_service.delete_recording(db, recording_id)


# ---------------------------------------------------------------------------
# Upload endpoints
# ---------------------------------------------------------------------------


@recordings_router.post("/upload-url", response_model=UploadUrlResponse)
async def request_upload_url(
    payload: UploadUrlRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadUrlResponse:
    """Generate a signed GCS upload URL for a recording."""
    result = await recording_service.generate_upload_url(
        db, payload.recording_id, payload.format, user.id
    )
    return UploadUrlResponse(**result)


@recordings_router.post("/{recording_id}/confirm-upload", response_model=RecordingResponse)
async def confirm_upload(
    recording_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecordingResponse:
    """Mark a recording as uploaded after file transfer to GCS."""
    existing = await recording_service.get_recording(db, recording_id)
    await recording_service.check_recording_access(db, existing, user.id)
    recording = await recording_service.confirm_upload(db, recording_id)
    return RecordingResponse.model_validate(recording)


# ---------------------------------------------------------------------------
# Split endpoint
# ---------------------------------------------------------------------------


@recordings_router.post("/{recording_id}/split", response_model=SplitResponse)
async def split_recording(
    recording_id: str,
    payload: SplitRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SplitResponse:
    """Split a recording into multiple segments using server-side FFmpeg.

    Each segment is saved as a new recording with its own GCS file.
    """
    new_ids = await split_service.split_recording(db, recording_id, payload.segments, user.id)
    return SplitResponse(recording_ids=new_ids)


# ---------------------------------------------------------------------------
# Cleaning endpoints
# ---------------------------------------------------------------------------


@recordings_router.post("/{recording_id}/clean", response_model=RecordingResponse)
async def trigger_cleaning(
    recording_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecordingResponse:
    """Trigger audio cleaning for a recording. Project manager only."""
    recording = await cleaning_service.trigger_cleaning(db, recording_id, user.id)
    return RecordingResponse.model_validate(recording)


@recordings_router.get("/{recording_id}/clean-status", response_model=CleaningStatusResponse)
async def get_cleaning_status(
    recording_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CleaningStatusResponse:
    """Get the current cleaning status of a recording."""
    recording = await cleaning_service.get_cleaning_status(db, recording_id)
    return CleaningStatusResponse(
        recording_id=recording.id,
        cleaning_status=recording.cleaning_status,
    )
