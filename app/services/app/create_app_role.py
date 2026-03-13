from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.db.models.auth import Role
from app.services.app.get_app_or_404 import get_app_or_404


async def create_app_role(
    db: AsyncSession,
    app_id: str,
    role_key: str,
    label: str,
    description: str | None = None,
) -> Role:

    app = await get_app_or_404(db, app_id)

    existing = await db.execute(
        select(Role).where(Role.app_id == app.id, Role.role_key == role_key)
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Role '{role_key}' already exists for this app")

    role = Role(
        app_id=app.id,
        role_key=role_key,
        label=label,
        description=description,
        is_system=False,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role
