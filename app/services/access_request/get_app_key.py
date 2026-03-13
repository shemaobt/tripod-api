from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import App


async def get_app_key(db: AsyncSession, app_id: str) -> str:

    result = await db.execute(select(App.app_key).where(App.id == app_id))
    app_key = result.scalar_one_or_none()
    if app_key is None:
        raise RuntimeError(f"App with id {app_id} not found")
    return app_key
