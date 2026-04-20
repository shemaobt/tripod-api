from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ACTIVE_UPLOAD_STATUSES
from app.core.exceptions import ConflictError, NotFoundError
from app.db.models.oc_recording import OC_Recording
from app.db.models.oc_storyteller import OC_Storyteller
from app.db.models.org import OrganizationMember
from app.db.models.project import Project, ProjectOrganizationAccess, ProjectUserAccess
from app.models.oc_project import OCProjectStatsResponse


async def get_user_project_role(db: AsyncSession, user_id: str, project_id: str) -> str | None:

    stmt = select(ProjectUserAccess.role).where(
        ProjectUserAccess.project_id == project_id,
        ProjectUserAccess.user_id == user_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_user_projects(db: AsyncSession, user_id: str) -> list[Project]:

    direct_project_ids = select(ProjectUserAccess.project_id).where(
        ProjectUserAccess.user_id == user_id
    )
    user_org_ids = select(OrganizationMember.organization_id).where(
        OrganizationMember.user_id == user_id
    )
    via_org_project_ids = select(ProjectOrganizationAccess.project_id).where(
        ProjectOrganizationAccess.organization_id.in_(user_org_ids)
    )

    stmt = (
        select(Project)
        .where(
            or_(
                Project.id.in_(direct_project_ids),
                Project.id.in_(via_org_project_ids),
            )
        )
        .order_by(Project.name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


async def list_all_projects(db: AsyncSession) -> list[Project]:

    stmt = select(Project).order_by(Project.name)
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


async def get_project_members(db: AsyncSession, project_id: str) -> list[ProjectUserAccess]:

    stmt = (
        select(ProjectUserAccess)
        .where(ProjectUserAccess.project_id == project_id)
        .order_by(ProjectUserAccess.granted_at)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def add_member(
    db: AsyncSession,
    project_id: str,
    user_id: str,
    role: str = "member",
    invited_by: str | None = None,
) -> ProjectUserAccess:

    stmt = select(ProjectUserAccess).where(
        ProjectUserAccess.project_id == project_id,
        ProjectUserAccess.user_id == user_id,
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ConflictError("User is already a member of this project")

    member = ProjectUserAccess(
        project_id=project_id,
        user_id=user_id,
        role=role,
        invited_by=invited_by,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def remove_member(db: AsyncSession, project_id: str, user_id: str) -> None:

    stmt = select(ProjectUserAccess).where(
        ProjectUserAccess.project_id == project_id,
        ProjectUserAccess.user_id == user_id,
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundError("User is not a member of this project")

    await db.delete(member)
    await db.commit()


async def get_project_stats(db: AsyncSession, project_id: str) -> OCProjectStatsResponse:

    rec_stmt = select(
        func.count(OC_Recording.id).label("total_recordings"),
        func.coalesce(func.sum(OC_Recording.duration_seconds), 0.0).label("total_duration_seconds"),
        func.coalesce(func.sum(OC_Recording.file_size_bytes), 0).label("total_file_size_bytes"),
    ).where(
        OC_Recording.project_id == project_id,
        OC_Recording.upload_status.in_(ACTIVE_UPLOAD_STATUSES),
    )
    rec_row = (await db.execute(rec_stmt)).one()

    st_stmt = select(func.count(OC_Storyteller.id)).where(OC_Storyteller.project_id == project_id)
    storyteller_count = (await db.execute(st_stmt)).scalar() or 0

    return OCProjectStatsResponse(
        project_id=project_id,
        total_recordings=rec_row.total_recordings,
        total_duration_seconds=float(rec_row.total_duration_seconds),
        total_file_size_bytes=int(rec_row.total_file_size_bytes),
        total_storytellers=int(storyteller_count),
    )


async def get_projects_batch_stats(
    db: AsyncSession, project_ids: list[str]
) -> dict[str, dict[str, int | float]]:
    """Return {project_id: {recordings, duration, storytellers}} for a batch of projects."""
    if not project_ids:
        return {}

    rec_stmt = (
        select(
            OC_Recording.project_id,
            func.count(OC_Recording.id).label("recordings"),
            func.coalesce(func.sum(OC_Recording.duration_seconds), 0.0).label("duration"),
        )
        .where(
            OC_Recording.project_id.in_(project_ids),
            OC_Recording.upload_status.in_(ACTIVE_UPLOAD_STATUSES),
        )
        .group_by(OC_Recording.project_id)
    )
    rec_rows = (await db.execute(rec_stmt)).all()

    st_stmt = (
        select(
            OC_Storyteller.project_id,
            func.count(OC_Storyteller.id).label("storytellers"),
        )
        .where(OC_Storyteller.project_id.in_(project_ids))
        .group_by(OC_Storyteller.project_id)
    )
    st_rows = (await db.execute(st_stmt)).all()

    result: dict[str, dict[str, int | float]] = {
        pid: {"recordings": 0, "duration": 0.0, "storytellers": 0} for pid in project_ids
    }
    for rec_row in rec_rows:
        result[rec_row.project_id]["recordings"] = int(rec_row.recordings)
        result[rec_row.project_id]["duration"] = float(rec_row.duration)
    for st_row in st_rows:
        result[st_row.project_id]["storytellers"] = int(st_row.storytellers)
    return result
