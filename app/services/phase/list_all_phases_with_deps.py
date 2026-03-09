from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.phase import Phase, PhaseDependency


async def list_all_phases_with_deps(db: AsyncSession) -> dict:
    """Return all phases with all dependencies in a single response."""
    phases_result = await db.execute(select(Phase).order_by(Phase.name))
    phases = list(phases_result.scalars().all())

    deps_result = await db.execute(select(PhaseDependency))
    all_deps = list(deps_result.scalars().all())

    deps_map: dict[str, list[str]] = {p.id: [] for p in phases}
    for dep in all_deps:
        if dep.phase_id in deps_map:
            deps_map[dep.phase_id].append(dep.depends_on_id)

    return {"phases": phases, "dependencies": deps_map}
