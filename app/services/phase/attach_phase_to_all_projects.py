from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.phase import ProjectPhase
from app.db.models.project import Project


async def attach_phase_to_all_projects(db: AsyncSession, phase_id: str) -> None:
    """Give every project a status row for this phase. Idempotent; the caller commits."""
    project_ids = (await db.execute(select(Project.id))).scalars().all()
    linked = (
        (await db.execute(select(ProjectPhase.project_id).where(ProjectPhase.phase_id == phase_id)))
        .scalars()
        .all()
    )
    for project_id in set(project_ids) - set(linked):
        db.add(ProjectPhase(project_id=project_id, phase_id=phase_id))
    await db.flush()
