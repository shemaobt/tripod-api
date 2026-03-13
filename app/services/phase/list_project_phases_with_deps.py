from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.phase import Phase, PhaseDependency, ProjectPhase
from app.models.phase import ProjectPhaseResponse, ProjectPhasesWithDepsResponse


async def list_project_phases_with_deps(
    db: AsyncSession,
    project_id: str,
) -> ProjectPhasesWithDepsResponse:

    stmt = (
        select(ProjectPhase, Phase)
        .join(Phase, ProjectPhase.phase_id == Phase.id)
        .where(ProjectPhase.project_id == project_id)
        .order_by(Phase.name)
    )
    result = await db.execute(stmt)
    rows = result.all()

    phase_ids = [phase.id for _, phase in rows]

    dep_stmt = (
        select(PhaseDependency)
        .where(PhaseDependency.phase_id.in_(phase_ids))
        .order_by(PhaseDependency.phase_id)
    )
    dep_result = await db.execute(dep_stmt)
    all_deps = dep_result.scalars().all()

    deps_map: dict[str, list[str]] = {pid: [] for pid in phase_ids}
    for dep in all_deps:
        if dep.phase_id in deps_map:
            deps_map[dep.phase_id].append(dep.depends_on_id)

    phases = [
        ProjectPhaseResponse(
            id=pp.id,
            phase_id=phase.id,
            phase_name=phase.name,
            phase_description=phase.description,
            status=pp.status,
        )
        for pp, phase in rows
    ]

    return ProjectPhasesWithDepsResponse(phases=phases, dependencies=deps_map)
