from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import App, Role, UserAppRole


async def list_user_apps(db: AsyncSession, user_id: str) -> list[tuple[App, list[str]]]:
    stmt = (
        select(App, Role.role_key)
        .join(UserAppRole, UserAppRole.app_id == App.id)
        .join(
            Role,
            and_(Role.id == UserAppRole.role_id, Role.app_id == App.id),
        )
        .where(UserAppRole.user_id == user_id, UserAppRole.revoked_at.is_(None))
        .order_by(App.name, Role.role_key)
    )
    result = await db.execute(stmt)
    rows = result.all()

    apps_dict: dict[str, tuple[App, list[str]]] = {}
    for app, role_key in rows:
        if app.id not in apps_dict:
            apps_dict[app.id] = (app, [])
        apps_dict[app.id][1].append(role_key)

    return list(apps_dict.values())
