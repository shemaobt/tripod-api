from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_cache import invalidate_roles
from app.core.exceptions import RoleError
from app.db.models.auth import UserAppRole
from app.services.authorization.get_app_by_key import get_app_by_key
from app.services.authorization.get_role import get_role


async def grant_app_role(
    db: AsyncSession,
    target_user_id: str,
    app_key: str,
    role_key: str,
    *,
    granted_by: str | None = None,
    commit: bool = True,
) -> UserAppRole:
    """Insert a UserAppRole without the admin-actor permission check.

    Use this from system-initiated paths like access-request approval, where the
    caller has already authorized the grant (or the grant is automated, e.g.
    app.auto_approve). For human-actor admin grants, use `assign_role` instead
    so the actor's permissions are verified.
    """
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
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    assignment = UserAppRole(
        user_id=target_user_id,
        app_id=app.id,
        role_id=role.id,
        granted_by=granted_by,
    )
    db.add(assignment)
    if commit:
        await db.commit()
        await db.refresh(assignment)
    else:
        await db.flush()
    invalidate_roles(target_user_id)
    return assignment
