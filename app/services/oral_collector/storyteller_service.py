from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.db.models.oc_storyteller import OC_Storyteller
from app.models.oc_storyteller import StorytellerCreate, StorytellerUpdate
from app.services.oral_collector.require_manager import require_project_manager


async def list_project_storytellers(db: AsyncSession, project_id: str) -> list[OC_Storyteller]:
    """Return all storytellers for a project, ordered by name."""
    stmt = (
        select(OC_Storyteller)
        .where(OC_Storyteller.project_id == project_id)
        .order_by(OC_Storyteller.name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_storyteller(db: AsyncSession, storyteller_id: str) -> OC_Storyteller:
    """Fetch a storyteller by id or raise NotFoundError."""
    stmt = select(OC_Storyteller).where(OC_Storyteller.id == storyteller_id)
    result = await db.execute(stmt)
    storyteller = result.scalar_one_or_none()
    if storyteller is None:
        raise NotFoundError("Storyteller not found")
    return storyteller


async def create_storyteller(
    db: AsyncSession,
    project_id: str,
    data: StorytellerCreate,
    user_id: str,
    *,
    is_platform_admin: bool = False,
) -> OC_Storyteller:
    """Create a storyteller for a project. Requires project manager role or platform admin."""
    await require_project_manager(
        db,
        project_id,
        user_id,
        action="create storytellers",
        is_platform_admin=is_platform_admin,
    )
    if not data.external_acceptance_confirmed:
        raise ValidationError(
            "External acceptance validation is required before registering a storyteller"
        )

    storyteller = OC_Storyteller(
        project_id=project_id,
        name=data.name,
        sex=data.sex,
        age=data.age,
        location=data.location,
        dialect=data.dialect,
        external_acceptance_confirmed=True,
        external_acceptance_confirmed_at=datetime.now(UTC),
        external_acceptance_confirmed_by=user_id,
    )
    db.add(storyteller)
    await db.commit()
    await db.refresh(storyteller)
    return storyteller


async def update_storyteller(
    db: AsyncSession,
    storyteller_id: str,
    data: StorytellerUpdate,
    user_id: str,
    *,
    is_platform_admin: bool = False,
) -> OC_Storyteller:
    """Update a storyteller's editable fields. Requires project manager role or platform admin."""
    storyteller = await get_storyteller(db, storyteller_id)
    await require_project_manager(
        db,
        storyteller.project_id,
        user_id,
        action="update storytellers",
        is_platform_admin=is_platform_admin,
    )

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(storyteller, field, value)
    await db.commit()
    await db.refresh(storyteller)
    return storyteller


async def delete_storyteller(
    db: AsyncSession,
    storyteller_id: str,
    user_id: str,
    *,
    is_platform_admin: bool = False,
) -> None:
    """Delete a storyteller. Linked recordings keep their data; storyteller_id is set to NULL."""
    storyteller = await get_storyteller(db, storyteller_id)
    await require_project_manager(
        db,
        storyteller.project_id,
        user_id,
        action="delete storytellers",
        is_platform_admin=is_platform_admin,
    )
    await db.delete(storyteller)
    await db.commit()
