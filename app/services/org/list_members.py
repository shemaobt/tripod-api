from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import User
from app.db.models.org import OrganizationMember


async def list_members(
    db: AsyncSession,
    organization_id: str,
) -> list[tuple[OrganizationMember, User]]:
    stmt: Select[tuple[OrganizationMember, User]] = (
        select(OrganizationMember, User)
        .join(User, OrganizationMember.user_id == User.id)
        .where(OrganizationMember.organization_id == organization_id)
        .order_by(OrganizationMember.joined_at)
    )
    result = await db.execute(stmt)
    return [row._tuple() for row in result.all()]
