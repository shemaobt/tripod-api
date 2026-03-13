from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError

T = TypeVar("T")


async def get_or_raise(
    db: AsyncSession, model: type[T], entity_id: str, *, label: str | None = None
) -> T:
    """Fetch a row by primary key or raise NotFoundError."""
    stmt = select(model).where(model.id == entity_id)  # type: ignore[attr-defined]
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        name = label or model.__name__  # type: ignore[attr-defined]
        raise NotFoundError(f"{name} {entity_id} not found")
    return row  # type: ignore[return-value]
