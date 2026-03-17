from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import App

OC_APP_KEY = "oral-collector"


async def get_oc_app_id(db: AsyncSession) -> str:
    stmt = select(App.id).where(App.app_key == OC_APP_KEY)
    result = await db.execute(stmt)
    app_id = result.scalar_one_or_none()
    if app_id is None:
        raise RuntimeError(f"App '{OC_APP_KEY}' not found in database")
    return app_id
