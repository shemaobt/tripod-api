from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import User


async def list_users(db: AsyncSession) -> list[User]:
    stmt: Select[tuple[User]] = select(User).order_by(User.email)
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())
