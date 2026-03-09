from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.phase import Phase, ProjectPhase


async def list_project_phases_with_details(
    db: AsyncSession,
    project_id: str,
) -> list[dict]:
    stmt = (
        select(ProjectPhase, Phase)
        .join(Phase, ProjectPhase.phase_id == Phase.id)
        .where(ProjectPhase.project_id == project_id)
        .order_by(Phase.name)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "id": pp.id,
            "phase_id": phase.id,
            "phase_name": phase.name,
            "phase_description": phase.description,
            "status": pp.status,
        }
        for pp, phase in rows
    ]
