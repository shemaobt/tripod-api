from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_middleware import get_current_user, require_platform_admin
from app.core.database import get_db
from app.db.models.auth import User
from app.models.oc_genre import (
    GenreCreate,
    GenreResponse,
    GenreUpdate,
    SubcategoryCreate,
    SubcategoryResponse,
    SubcategoryUpdate,
)
from app.services.oral_collector import genre_service

genres_router = APIRouter()
subcategories_router = APIRouter()

@genres_router.get("", response_model=list[GenreResponse])
async def list_genres(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GenreResponse]:

    genres = await genre_service.list_genres(db)
    return [GenreResponse.model_validate(g) for g in genres]

@genres_router.post(
    "",
    response_model=GenreResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_genre(
    payload: GenreCreate,
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> GenreResponse:

    genre = await genre_service.create_genre(db, payload)
    return GenreResponse.model_validate(genre)

@genres_router.patch("/{genre_id}", response_model=GenreResponse)
async def update_genre(
    genre_id: str,
    payload: GenreUpdate,
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> GenreResponse:

    genre = await genre_service.update_genre(db, genre_id, payload)
    return GenreResponse.model_validate(genre)

@genres_router.delete("/{genre_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_genre(
    genre_id: str,
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> None:

    await genre_service.delete_genre(db, genre_id)

@genres_router.post(
    "/{genre_id}/subcategories",
    response_model=SubcategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_subcategory(
    genre_id: str,
    payload: SubcategoryCreate,
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> SubcategoryResponse:

    subcategory = await genre_service.create_subcategory(db, genre_id, payload)
    return SubcategoryResponse.model_validate(subcategory)

@subcategories_router.patch("/{subcategory_id}", response_model=SubcategoryResponse)
async def update_subcategory(
    subcategory_id: str,
    payload: SubcategoryUpdate,
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> SubcategoryResponse:

    subcategory = await genre_service.update_subcategory(db, subcategory_id, payload)
    return SubcategoryResponse.model_validate(subcategory)

@subcategories_router.delete("/{subcategory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subcategory(
    subcategory_id: str,
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> None:

    await genre_service.delete_subcategory(db, subcategory_id)
