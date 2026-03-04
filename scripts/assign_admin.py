import asyncio
import sys

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.db.models.auth import App, Role, User, UserAppRole


async def main():
    email = sys.argv[1]
    app_key = "meaning-map-generator"
    role_key = "admin"

    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if not user:
            print(f"User {email} not found")
            return

        app = (await db.execute(select(App).where(App.app_key == app_key))).scalar_one_or_none()
        role = (
            await db.execute(select(Role).where(Role.app_id == app.id, Role.role_key == role_key))
        ).scalar_one_or_none()

        existing = (
            await db.execute(
                select(UserAppRole).where(
                    UserAppRole.user_id == user.id, UserAppRole.app_id == app.id
                )
            )
        ).scalar_one_or_none()

        if existing:
            existing.role_id = role.id
        else:
            db.add(UserAppRole(user_id=user.id, app_id=app.id, role_id=role.id))

        await db.commit()
        print(f"Assigned {role_key} to {email} for {app_key}")


if __name__ == "__main__":
    asyncio.run(main())
