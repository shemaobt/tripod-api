from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.db.models.public_request import PublicRequest
from app.services.language.get_language_by_code import get_language_by_code


async def create_language_request(
    db: AsyncSession,
    requester_name: str,
    requester_email: str,
    name: str,
    code: str,
) -> PublicRequest:
    normalized_code = code.lower()
    existing = await get_language_by_code(db, normalized_code)
    if existing:
        raise ConflictError("Language code already exists")

    stmt: Select[tuple[PublicRequest]] = (
        select(PublicRequest)
        .where(
            PublicRequest.kind == "create_language",
            PublicRequest.status == "pending",
            PublicRequest.code == normalized_code,
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ConflictError("A pending request for this language code already exists")

    request = PublicRequest(
        kind="create_language",
        requester_name=requester_name,
        requester_email=requester_email,
        name=name,
        code=normalized_code,
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request
