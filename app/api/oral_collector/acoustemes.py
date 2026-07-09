from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.db.models.auth import User
from app.models.oc_acousteme import (
    AcoustemeArtifactResponse,
    AcoustemeStreamResponse,
)
from app.services.oral_collector import acousteme_service

acoustemes_router = APIRouter()


@acoustemes_router.get("/{recording_id}", response_model=AcoustemeArtifactResponse)
async def get_acousteme_artifact(
    recording_id: str,
    codebook_version: str | None = Query(
        None, description="Pin a codebook version; defaults to the newest"
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AcoustemeArtifactResponse:
    """Metadata for a recording's acousteme stream (newest version by default)."""

    artifact = await acousteme_service.get_artifact(
        db, recording_id, user.id, codebook_version=codebook_version
    )
    return AcoustemeArtifactResponse.model_validate(artifact)


@acoustemes_router.get("/{recording_id}/versions", response_model=list[AcoustemeArtifactResponse])
async def list_acousteme_versions(
    recording_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AcoustemeArtifactResponse]:
    """Every codebook version available for a recording, newest first."""

    artifacts = await acousteme_service.list_artifacts(db, recording_id, user.id)
    return [AcoustemeArtifactResponse.model_validate(a) for a in artifacts]


@acoustemes_router.get("/{recording_id}/stream", response_model=AcoustemeStreamResponse)
async def get_acousteme_stream(
    recording_id: str,
    codebook_version: str | None = Query(
        None, description="Pin a codebook version; defaults to the newest"
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AcoustemeStreamResponse:
    """Signed download URL + grid metadata for the frontend to load and chunk."""

    return await acousteme_service.get_stream(
        db, recording_id, user.id, codebook_version=codebook_version
    )
