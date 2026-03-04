from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_cache import invalidate_roles
from app.core.exceptions import RoleError
from app.db.models.auth import User, UserAppRole
from app.services.authorization.assert_can_manage_roles import assert_can_manage_roles
from app.services.authorization.get_app_by_key import get_app_by_key
from app.services.authorization.get_role import get_role


async def assign_role(
    db: AsyncSession,
    actor_user: User,
    target_user_id: str,
    app_key: str,
    role_key: str,
) -> UserAppRole:
    """Assign role to a target user in app context."""
    await assert_can_manage_roles(db, actor_user, app_key)

    app = await get_app_by_key(db, app_key)
    if not app:
        raise RoleError("App not found")

    role = await get_role(db, app.id, role_key)
    if not role:
        raise RoleError("Role not found")

    stmt: Select[tuple[UserAppRole]] = select(UserAppRole).where(
        UserAppRole.user_id == target_user_id,
        UserAppRole.app_id == app.id,
        UserAppRole.role_id == role.id,
        UserAppRole.revoked_at.is_(None),
    )
    result = await db.execute(stmt)
    assignment = result.scalar_one_or_none()
    if assignment:
        return assignment

    assignment = UserAppRole(
        user_id=target_user_id,
        app_id=app.id,
        role_id=role.id,
        granted_by=actor_user.id,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    invalidate_roles(target_user_id)
    return assignment
