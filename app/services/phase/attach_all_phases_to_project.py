from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.phase import Phase, ProjectPhase


async def attach_all_phases_to_project(db: AsyncSession, project_id: str) -> None:
    """Give this project a status row for every phase. Idempotent; the caller commits."""
    phase_ids = (await db.execute(select(Phase.id))).scalars().all()
    linked = (
        (
            await db.execute(
                select(ProjectPhase.phase_id).where(ProjectPhase.project_id == project_id)
            )
        )
        .scalars()
        .all()
    )
    for phase_id in set(phase_ids) - set(linked):
        db.add(ProjectPhase(project_id=project_id, phase_id=phase_id))
    await db.flush()
