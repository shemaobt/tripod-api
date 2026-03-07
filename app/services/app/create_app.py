from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.db.models.auth import App


async def create_app(
    db: AsyncSession,
    app_key: str,
    name: str,
    description: str | None = None,
    icon_url: str | None = None,
    app_url: str | None = None,
    ios_url: str | None = None,
    android_url: str | None = None,
    platform: str = "web",
    is_active: bool = True,
) -> App:
    existing = await db.execute(select(App).where(App.app_key == app_key))
    if existing.scalar_one_or_none():
        raise ConflictError(f"App with key '{app_key}' already exists")

    app = App(
        app_key=app_key,
        name=name,
        description=description,
        icon_url=icon_url,
        app_url=app_url,
        ios_url=ios_url,
        android_url=android_url,
        platform=platform,
        is_active=is_active,
    )
    db.add(app)
    await db.flush()
    await db.refresh(app)
    return app
