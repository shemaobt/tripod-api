from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.db.models.auth import User
from app.models.oc_storyteller import (
    StorytellerCreate,
    StorytellerResponse,
    StorytellerUpdate,
)
from app.services.oral_collector import storyteller_service
from app.services.oral_collector.require_access import require_project_access

project_storytellers_router = APIRouter()
storytellers_router = APIRouter()


@project_storytellers_router.get(
    "/{project_id}/storytellers", response_model=list[StorytellerResponse]
)
async def list_project_storytellers(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[StorytellerResponse]:
    await require_project_access(db, project_id, user)
    rows = await storyteller_service.list_project_storytellers(db, project_id)
    return [StorytellerResponse.model_validate(r) for r in rows]


@project_storytellers_router.post(
    "/{project_id}/storytellers",
    response_model=StorytellerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_storyteller(
    project_id: str,
    payload: StorytellerCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StorytellerResponse:
    storyteller = await storyteller_service.create_storyteller(
        db,
        project_id,
        payload,
        user.id,
        is_platform_admin=user.is_platform_admin,
    )
    return StorytellerResponse.model_validate(storyteller)


@storytellers_router.get("/{storyteller_id}", response_model=StorytellerResponse)
async def get_storyteller(
    storyteller_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StorytellerResponse:
    storyteller = await storyteller_service.get_storyteller(db, storyteller_id)
    await require_project_access(db, storyteller.project_id, user)
    return StorytellerResponse.model_validate(storyteller)


@storytellers_router.patch("/{storyteller_id}", response_model=StorytellerResponse)
async def update_storyteller(
    storyteller_id: str,
    payload: StorytellerUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StorytellerResponse:
    storyteller = await storyteller_service.update_storyteller(
        db,
        storyteller_id,
        payload,
        user.id,
        is_platform_admin=user.is_platform_admin,
    )
    return StorytellerResponse.model_validate(storyteller)


@storytellers_router.delete("/{storyteller_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_storyteller(
    storyteller_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await storyteller_service.delete_storyteller(
        db,
        storyteller_id,
        user.id,
        is_platform_admin=user.is_platform_admin,
    )
