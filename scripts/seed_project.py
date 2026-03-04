import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.db.models.auth import User
from app.db.models.project import Project, ProjectUserAccess


async def main():
    email = "admin@shemaywam.com"
    project_name = "Default Meaning Map Project"

    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if not user:
            print(f"User {email} not found")
            return

        project = (
            await db.execute(select(Project).where(Project.name == project_name))
        ).scalar_one_or_none()

        if not project:
            # Need a language ID. Let's just create one or grab the first one.
            from app.db.models.language import Language

            lang = (await db.execute(select(Language))).scalars().first()
            if not lang:
                lang = Language(id="eng", name="English", code="en")
                db.add(lang)
                await db.flush()

            project = Project(
                name=project_name,
                language_id=lang.id,
                description="Default project for testing Meaning Maps",
            )
            db.add(project)
            await db.flush()

        # Give access
        access = (
            await db.execute(
                select(ProjectUserAccess).where(
                    ProjectUserAccess.project_id == project.id, ProjectUserAccess.user_id == user.id
                )
            )
        ).scalar_one_or_none()

        if not access:
            db.add(ProjectUserAccess(project_id=project.id, user_id=user.id))

        await db.commit()
        print(f"Created/found project '{project_name}' and granted access to {email}")


if __name__ == "__main__":
    asyncio.run(main())
