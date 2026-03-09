from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.db.models.org import Organization
from app.services.org.get_organization_by_slug import get_organization_by_slug
from app.services.org.get_organization_or_404 import get_organization_or_404


async def update_organization(
    db: AsyncSession,
    organization_id: str,
    name: str | None = None,
    slug: str | None = None,
    description: str | None = None,
    logo_url: str | None = None,
    manager_id: str | None = None,
) -> Organization:
    org = await get_organization_or_404(db, organization_id)
    if slug is not None:
        existing = await get_organization_by_slug(db, slug)
        if existing and existing.id != org.id:
            raise ConflictError("Organization slug already exists")
        org.slug = slug.lower()
    if name is not None:
        org.name = name
    if description is not None:
        org.description = description
    if logo_url is not None:
        org.logo_url = logo_url
    if manager_id is not None:
        org.manager_id = manager_id
    await db.commit()
    await db.refresh(org)
    return org
