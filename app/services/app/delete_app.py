from sqlalchemy.ext.asyncio import AsyncSession

from app.services.app.get_app_or_404 import get_app_or_404


async def delete_app(db: AsyncSession, app_id: str) -> None:
    app = await get_app_or_404(db, app_id)
    await db.delete(app)
    await db.commit()
