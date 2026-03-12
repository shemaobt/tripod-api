from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.db.models.oc_genre import OC_Genre, OC_Subcategory
from app.models.oc_genre import (
    GenreCreate,
    GenreUpdate,
    SubcategoryCreate,
    SubcategoryUpdate,
)

async def list_genres(db: AsyncSession) -> list[OC_Genre]:

    stmt = (
        select(OC_Genre)
        .where(OC_Genre.is_active.is_(True))
        .options(selectinload(OC_Genre.subcategories))
        .order_by(OC_Genre.sort_order)
    )
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())

async def get_genre(db: AsyncSession, genre_id: str) -> OC_Genre:

    stmt = (
        select(OC_Genre)
        .where(OC_Genre.id == genre_id)
        .options(selectinload(OC_Genre.subcategories))
    )
    result = await db.execute(stmt)
    genre = result.scalar_one_or_none()
    if not genre:
        raise NotFoundError("Genre not found")
    return genre

async def create_genre(db: AsyncSession, data: GenreCreate) -> OC_Genre:

    genre = OC_Genre(
        name=data.name,
        description=data.description,
        icon=data.icon,
        color=data.color,
        sort_order=data.sort_order,
    )
    db.add(genre)
    await db.commit()
    await db.refresh(genre, attribute_names=["subcategories"])
    return genre

async def update_genre(db: AsyncSession, genre_id: str, data: GenreUpdate) -> OC_Genre:

    genre = await get_genre(db, genre_id)
    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(genre, field, value)
    await db.commit()
    await db.refresh(genre, attribute_names=["subcategories"])
    return genre

async def delete_genre(db: AsyncSession, genre_id: str) -> None:

    genre = await get_genre(db, genre_id)
    genre.is_active = False
    await db.commit()

async def _get_subcategory(db: AsyncSession, subcategory_id: str) -> OC_Subcategory:

    stmt = select(OC_Subcategory).where(OC_Subcategory.id == subcategory_id)
    result = await db.execute(stmt)
    subcategory = result.scalar_one_or_none()
    if not subcategory:
        raise NotFoundError("Subcategory not found")
    return subcategory

async def create_subcategory(
    db: AsyncSession, genre_id: str, data: SubcategoryCreate
) -> OC_Subcategory:

    await get_genre(db, genre_id)
    subcategory = OC_Subcategory(
        genre_id=genre_id,
        name=data.name,
        description=data.description,
        sort_order=data.sort_order,
    )
    db.add(subcategory)
    await db.commit()
    await db.refresh(subcategory)
    return subcategory

async def update_subcategory(
    db: AsyncSession, subcategory_id: str, data: SubcategoryUpdate
) -> OC_Subcategory:

    subcategory = await _get_subcategory(db, subcategory_id)
    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(subcategory, field, value)
    await db.commit()
    await db.refresh(subcategory)
    return subcategory

async def delete_subcategory(db: AsyncSession, subcategory_id: str) -> None:

    subcategory = await _get_subcategory(db, subcategory_id)
    subcategory.is_active = False
    await db.commit()
