from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import User

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:

    stmt: Select[tuple[User]] = select(User).where(User.email == email.lower())
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
