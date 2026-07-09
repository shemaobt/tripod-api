from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.db.models.auth import User
from app.models.oc_acousteme import (
    AcoustemeArtifactResponse,
    AcoustemeAudioResponse,
    AcoustemeListItem,
    AcoustemeStreamResponse,
)
from app.services.oral_collector import acousteme_service

acoustemes_router = APIRouter()


@acoustemes_router.get("", response_model=list[AcoustemeListItem])
async def list_acoustemes(
    collection: str = Query(..., description="Collection label, e.g. terena-ruth"),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AcoustemeListItem]:
    """List every ready acousteme artifact in a collection."""

    artifacts = await acousteme_service.list_by_collection(db, collection)
    return [AcoustemeListItem.model_validate(a) for a in artifacts]


@acoustemes_router.get("/{audio_id}", response_model=AcoustemeArtifactResponse)
async def get_acousteme_artifact(
    audio_id: str,
    codebook_version: str | None = Query(
        None, description="Pin a codebook version; defaults to the newest"
    ),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AcoustemeArtifactResponse:
    """Metadata for an audio's acousteme stream (newest version by default)."""

    artifact = await acousteme_service.get_artifact(db, audio_id, codebook_version=codebook_version)
    return AcoustemeArtifactResponse.model_validate(artifact)


@acoustemes_router.get("/{audio_id}/versions", response_model=list[AcoustemeArtifactResponse])
async def list_acousteme_versions(
    audio_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AcoustemeArtifactResponse]:
    """Every codebook version available for an audio, newest first."""

    artifacts = await acousteme_service.list_artifacts(db, audio_id)
    return [AcoustemeArtifactResponse.model_validate(a) for a in artifacts]


@acoustemes_router.get("/{audio_id}/stream", response_model=AcoustemeStreamResponse)
async def get_acousteme_stream(
    audio_id: str,
    codebook_version: str | None = Query(
        None, description="Pin a codebook version; defaults to the newest"
    ),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AcoustemeStreamResponse:
    """Signed download URL + grid metadata for the frontend to load and chunk."""

    return await acousteme_service.get_stream(db, audio_id, codebook_version=codebook_version)


@acoustemes_router.get("/{audio_id}/audio", response_model=AcoustemeAudioResponse)
async def get_acousteme_audio(
    audio_id: str,
    codebook_version: str | None = Query(
        None, description="Pin a codebook version; defaults to the newest"
    ),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AcoustemeAudioResponse:
    """Signed download URL for the source audio file."""

    return await acousteme_service.get_audio_url(db, audio_id, codebook_version=codebook_version)
