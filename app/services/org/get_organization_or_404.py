from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.org import Organization
from app.services.common import get_or_raise


async def get_organization_or_404(db: AsyncSession, organization_id: str) -> Organization:
    return await get_or_raise(db, Organization, organization_id, label="Organization")
