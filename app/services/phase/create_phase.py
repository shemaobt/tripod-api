from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.phase import Phase
from app.models.phase import PhaseCreate
from app.services.phase.attach_phase_to_all_projects import attach_phase_to_all_projects


async def create_phase(db: AsyncSession, payload: PhaseCreate) -> Phase:
    """Create a platform phase and attach it to every existing project."""
    phase = Phase(name=payload.name, description=payload.description)
    db.add(phase)
    await db.flush()
    await attach_phase_to_all_projects(db, phase.id)
    await db.commit()
    await db.refresh(phase)
    return phase
