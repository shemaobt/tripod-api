from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project_health import PHAgentPrompt
from app.services.project_health.agents._default_prompts import iter_defaults


async def seed_default_prompts(db: AsyncSession) -> int:
    """Insert any missing default prompt rows. Idempotent — returns the number
    of rows inserted in this call."""
    existing_keys = {key for (key,) in (await db.execute(select(PHAgentPrompt.prompt_key))).all()}
    inserted = 0
    for prompt_key, defaults in iter_defaults():
        if prompt_key in existing_keys:
            continue
        db.add(
            PHAgentPrompt(
                prompt_key=prompt_key,
                name=defaults["name"],
                description=defaults["description"],
                template=defaults["template"],
                version=1,
            )
        )
        inserted += 1
    if inserted:
        await db.commit()
    return inserted
