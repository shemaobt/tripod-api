from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import App
from app.services.common import get_or_raise


async def get_app_or_404(db: AsyncSession, app_id: str) -> App:
    return await get_or_raise(db, App, app_id, label="App")
