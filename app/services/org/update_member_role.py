from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.org import OrganizationMember


async def update_member_role(
    db: AsyncSession,
    organization_id: str,
    user_id: str,
    role: str,
) -> OrganizationMember:
    stmt: Select[tuple[OrganizationMember]] = select(OrganizationMember).where(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == user_id,
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundError("Member not found in organization")
    member.role = role
    await db.commit()
    await db.refresh(member)
    return member
