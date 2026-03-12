from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.db.models.auth import Role

async def delete_app_role(db: AsyncSession, app_id: str, role_id: str) -> None:

    stmt = select(Role).where(Role.id == role_id, Role.app_id == app_id)
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()

    if not role:
        raise NotFoundError("Role not found")
    if role.is_system:
        raise ConflictError("System roles cannot be deleted")

    await db.delete(role)
    await db.commit()
