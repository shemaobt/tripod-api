from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user.get_user_by_id import get_user_by_id

async def delete_user(db: AsyncSession, user_id: str) -> None:

    user = await get_user_by_id(db, user_id)
    await db.delete(user)
    await db.commit()
