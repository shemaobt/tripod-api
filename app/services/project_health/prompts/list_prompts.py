from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project_health import PHAgentPrompt
from app.services.project_health.agents._default_prompts import PROMPT_KEYS


async def list_prompts(db: AsyncSession) -> list[PHAgentPrompt]:
    """Return all PH prompt rows in the canonical PROMPT_KEYS order."""
    stmt = select(PHAgentPrompt)
    rows = list((await db.execute(stmt)).scalars().all())
    order = {key: idx for idx, key in enumerate(PROMPT_KEYS)}
    rows.sort(key=lambda r: order.get(r.prompt_key, len(order)))
    return rows
