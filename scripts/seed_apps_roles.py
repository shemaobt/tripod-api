import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.db.models.auth import App, Role

SEED_APPS = [
    ("tripod-studio", "Tripod Studio"),
    ("meaning-map-generator", "Meaning Map Generator"),
    ("oral-bridge", "Oral Bridge"),
    ("oral-collector", "Oral Collector"),
    ("avita", "AViTA"),
]

SEED_ROLES = [
    "admin",
    "facilitator",
    "reviewer",
    "annotator",
    "viewer",
    "exegete",
    "biblical_language_specialist",
    "translation_specialist",
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        for app_key, app_name in SEED_APPS:
            result = await db.execute(select(App).where(App.app_key == app_key))
            app = result.scalar_one_or_none()
            if not app:
                app = App(app_key=app_key, name=app_name)
                db.add(app)
                await db.flush()

            for role_key in SEED_ROLES:
                role_result = await db.execute(
                    select(Role).where(Role.app_id == app.id, Role.role_key == role_key)
                )
                role = role_result.scalar_one_or_none()
                if not role:
                    db.add(
                        Role(
                            app_id=app.id,
                            role_key=role_key,
                            label=role_key.replace("-", " ").title(),
                            is_system=True,
                        )
                    )

        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
