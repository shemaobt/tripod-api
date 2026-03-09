from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.db.models.oc_project_user import OC_ProjectUser
from app.db.models.oc_recording import OC_Recording
from app.db.models.project import Project


async def list_user_projects(db: AsyncSession, user_id: str) -> list[Project]:
    """Return all projects the user is a member of."""
    stmt = (
        select(Project)
        .join(OC_ProjectUser, OC_ProjectUser.project_id == Project.id)
        .where(OC_ProjectUser.user_id == user_id)
        .order_by(Project.name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_project_members(
    db: AsyncSession, project_id: str
) -> list[OC_ProjectUser]:
    """Return all members of a project."""
    stmt = (
        select(OC_ProjectUser)
        .where(OC_ProjectUser.project_id == project_id)
        .order_by(OC_ProjectUser.joined_at)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def add_member(
    db: AsyncSession, project_id: str, user_id: str, role: str = "user"
) -> OC_ProjectUser:
    """Add a user to a project. Raises ConflictError if already a member."""
    # Check membership doesn't already exist
    stmt = select(OC_ProjectUser).where(
        OC_ProjectUser.project_id == project_id,
        OC_ProjectUser.user_id == user_id,
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ConflictError("User is already a member of this project")

    member = OC_ProjectUser(
        project_id=project_id,
        user_id=user_id,
        role=role,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def remove_member(
    db: AsyncSession, project_id: str, user_id: str
) -> None:
    """Remove a user from a project. Raises NotFoundError if not a member."""
    stmt = select(OC_ProjectUser).where(
        OC_ProjectUser.project_id == project_id,
        OC_ProjectUser.user_id == user_id,
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundError("User is not a member of this project")

    await db.delete(member)
    await db.commit()


async def get_project_stats(
    db: AsyncSession, project_id: str
) -> dict:
    """Return aggregate recording stats for a project."""
    stmt = select(
        func.count(OC_Recording.id).label("total_recordings"),
        func.coalesce(func.sum(OC_Recording.duration_seconds), 0.0).label(
            "total_duration_seconds"
        ),
        func.coalesce(func.sum(OC_Recording.file_size_bytes), 0).label(
            "total_file_size_bytes"
        ),
    ).where(OC_Recording.project_id == project_id)

    result = await db.execute(stmt)
    row = result.one()
    return {
        "project_id": project_id,
        "total_recordings": row.total_recordings,
        "total_duration_seconds": float(row.total_duration_seconds),
        "total_file_size_bytes": int(row.total_file_size_bytes),
    }
