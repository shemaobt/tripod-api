from __future__ import annotations

from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError

T = TypeVar("T")


async def get_or_404(
    db: AsyncSession, model: type[T], entity_id: str, label: str = "Resource"
) -> T:
    stmt = select(model).where(model.id == entity_id)  # type: ignore[attr-defined]
    result = await db.execute(stmt)
    obj = result.scalar_one_or_none()
    if obj is None:
        raise NotFoundError(f"{label} not found")
    return obj  # type: ignore[return-value]
