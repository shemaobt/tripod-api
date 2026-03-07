from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import Role


async def list_app_roles(db: AsyncSession, app_id: str) -> list[Role]:
    stmt = select(Role).where(Role.app_id == app_id).order_by(Role.role_key)
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())
