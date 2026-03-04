from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import App

MM_APP_KEY = "meaning-map-generator"


async def get_mm_app_id(db: AsyncSession) -> str:
    """Return the app id for the meaning-map-generator app."""
    stmt = select(App.id).where(App.app_key == MM_APP_KEY)
    result = await db.execute(stmt)
    app_id = result.scalar_one_or_none()
    if app_id is None:
        raise RuntimeError(f"App '{MM_APP_KEY}' not found in database")
    return app_id
