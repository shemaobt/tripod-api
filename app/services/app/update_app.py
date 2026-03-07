from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import App
from app.services.app.get_app_or_404 import get_app_or_404


async def update_app(
    db: AsyncSession,
    app_id: str,
    name: str | None = None,
    description: str | None = None,
    icon_url: str | None = None,
    app_url: str | None = None,
    ios_url: str | None = None,
    android_url: str | None = None,
    platform: str | None = None,
    is_active: bool | None = None,
) -> App:
    app = await get_app_or_404(db, app_id)
    if name is not None:
        app.name = name
    if description is not None:
        app.description = description
    if icon_url is not None:
        app.icon_url = icon_url
    if app_url is not None:
        app.app_url = app_url
    if ios_url is not None:
        app.ios_url = ios_url
    if android_url is not None:
        app.android_url = android_url
    if platform is not None:
        app.platform = platform
    if is_active is not None:
        app.is_active = is_active
    await db.flush()
    await db.refresh(app)
    return app
