from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import App


async def list_apps(db: AsyncSession) -> list[App]:
    stmt: Select[tuple[App]] = select(App).order_by(App.name)
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())
