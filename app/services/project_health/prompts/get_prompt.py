from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.project_health import PHAgentPrompt
from app.services.project_health.agents._default_prompts import PROMPT_KEYS


async def get_prompt_or_404(db: AsyncSession, prompt_key: str) -> PHAgentPrompt:
    if prompt_key not in PROMPT_KEYS:
        raise NotFoundError(f"Unknown prompt key: {prompt_key}")
    stmt = select(PHAgentPrompt).where(PHAgentPrompt.prompt_key == prompt_key)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise NotFoundError(f"Prompt {prompt_key} not seeded")
    return row
