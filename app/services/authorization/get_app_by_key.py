from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import App

async def get_app_by_key(db: AsyncSession, app_key: str) -> App | None:

    stmt: Select[tuple[App]] = select(App).where(App.app_key == app_key)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
