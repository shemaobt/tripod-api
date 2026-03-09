from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.db.models.org import Organization
from app.services.org.get_organization_by_slug import get_organization_by_slug


async def create_organization(
    db: AsyncSession,
    name: str,
    slug: str,
    description: str | None = None,
    logo_url: str | None = None,
    manager_id: str | None = None,
) -> Organization:
    existing = await get_organization_by_slug(db, slug)
    if existing:
        raise ConflictError("Organization slug already exists")
    org = Organization(
        name=name,
        slug=slug.lower(),
        description=description,
        logo_url=logo_url,
        manager_id=manager_id,
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org
