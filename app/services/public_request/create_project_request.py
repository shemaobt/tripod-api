from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.public_request import PublicRequest
from app.services.language.get_language_or_404 import get_language_or_404


async def create_project_request(
    db: AsyncSession,
    requester_name: str,
    requester_email: str,
    name: str,
    language_id: str,
    description: str | None = None,
) -> PublicRequest:
    await get_language_or_404(db, language_id)

    request = PublicRequest(
        kind="create_project",
        requester_name=requester_name,
        requester_email=requester_email,
        name=name,
        language_id=language_id,
        description=description,
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request
