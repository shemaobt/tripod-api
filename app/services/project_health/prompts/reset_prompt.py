from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project_health import PHAgentPrompt
from app.services.project_health.agents._default_prompts import get_default
from app.services.project_health.prompts.get_prompt import get_prompt_or_404


async def reset_prompt(db: AsyncSession, prompt_key: str, *, updated_by: str) -> PHAgentPrompt:
    row = await get_prompt_or_404(db, prompt_key)
    defaults = get_default(prompt_key)
    bumped = False
    if row.template != defaults["template"]:
        row.template = defaults["template"]
        row.version = (row.version or 1) + 1
        bumped = True
    if row.name != defaults["name"]:
        row.name = defaults["name"]
    if row.description != defaults["description"]:
        row.description = defaults["description"]
    if bumped:
        row.updated_by = updated_by
    await db.commit()
    await db.refresh(row)
    return row
