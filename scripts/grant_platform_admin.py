"""Promote a user to platform admin by email.

Usage (in backend container):
    uv run python scripts/grant_platform_admin.py marcia.suzuki@uofn.edu
"""

import asyncio
import sys

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.db.models.auth import User


async def main() -> None:
    if len(sys.argv) != 2:
        print("usage: grant_platform_admin.py <email>")
        sys.exit(2)
    email = sys.argv[1].lower()
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user is None:
            print(f"user {email} not found")
            sys.exit(1)
        if user.is_platform_admin:
            print(f"user {email} is already a platform admin")
            return
        user.is_platform_admin = True
        await db.commit()
        print(f"granted platform admin to {email}")


if __name__ == "__main__":
    asyncio.run(main())
