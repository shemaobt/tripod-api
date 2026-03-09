from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.phase import Phase
from app.models.phase import PhaseUpdate
from app.services.phase.get_phase_or_404 import get_phase_or_404


async def update_phase(db: AsyncSession, phase_id: str, payload: PhaseUpdate) -> Phase:
    phase = await get_phase_or_404(db, phase_id)
    if payload.name is not None:
        phase.name = payload.name
    if payload.description is not None:
        phase.description = payload.description
    await db.commit()
    await db.refresh(phase)
    return phase
