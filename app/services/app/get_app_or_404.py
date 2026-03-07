from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.auth import App


async def get_app_or_404(db: AsyncSession, app_id: str) -> App:
    stmt = select(App).where(App.id == app_id)
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()
    if not app:
        raise NotFoundError(f"App {app_id} not found")
    return app
