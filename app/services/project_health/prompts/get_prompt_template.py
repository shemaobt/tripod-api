from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project_health import PHAgentPrompt
from app.services.project_health.agents._default_prompts import get_default_template


async def get_prompt_template(db: AsyncSession, prompt_key: str) -> str:
    """Return the editable template for ``prompt_key``.

    DB row wins if present, otherwise falls back to the baked-in default so
    the agent never breaks when the seed has not yet run.
    """
    stmt = select(PHAgentPrompt.template).where(PHAgentPrompt.prompt_key == prompt_key)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is not None:
        return row
    return get_default_template(prompt_key)
