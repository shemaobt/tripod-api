from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import User


async def search_users(db: AsyncSession, query: str) -> list[User]:
    stmt: Select[tuple[User]] = select(User).where(User.is_active == True)
    if query.strip():
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                User.email.ilike(pattern),
                User.display_name.ilike(pattern),
            )
        )
    stmt = stmt.order_by(User.email).limit(50)
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())
