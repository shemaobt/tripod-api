from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.phase import Phase
from app.services.common import get_or_raise


async def get_phase_or_404(db: AsyncSession, phase_id: str) -> Phase:
    return await get_or_raise(db, Phase, phase_id, label="Phase")
