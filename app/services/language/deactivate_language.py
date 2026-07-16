from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ConflictError
from app.db.models.auth import User
from app.db.models.language import Language
from app.db.models.project import Project
from app.services.language.get_language_or_404 import get_language_or_404


async def deactivate_language(db: AsyncSession, language_id: str, actor: User) -> Language:
    language = await get_language_or_404(db, language_id)

    if not actor.is_platform_admin:
        if language.created_by != actor.id:
            raise AuthorizationError("You can only deactivate languages you created")
        result = await db.execute(select(Project.name).where(Project.language_id == language_id))
        project_names = list(result.scalars().all())
        if project_names:
            joined = ", ".join(project_names)
            raise ConflictError(
                f"Cannot deactivate '{language.name}': it is used by "
                f"{len(project_names)} project(s): {joined}"
            )

    language.is_active = False
    await db.commit()
    await db.refresh(language)
    return language
