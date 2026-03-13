from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import Role


async def get_role(db: AsyncSession, app_id: str, role_key: str) -> Role | None:

    stmt: Select[tuple[Role]] = select(Role).where(Role.app_id == app_id, Role.role_key == role_key)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
