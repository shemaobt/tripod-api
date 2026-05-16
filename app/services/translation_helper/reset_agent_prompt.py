from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.translation_helper import AgentId, THAgentPrompt
from app.services.translation_helper._default_prompts import get_default_prompt
from app.services.translation_helper.get_agent_prompt import get_agent_prompt


async def reset_agent_prompt_to_default(
    db: AsyncSession,
    agent_id: AgentId,
    *,
    updated_by: str,
) -> THAgentPrompt:
    row = await get_agent_prompt(db, agent_id)
    default = get_default_prompt(agent_id)
    changed = (
        row.name != default["name"]
        or row.description != default["description"]
        or row.prompt != default["prompt"]
    )
    row.name = default["name"]
    row.description = default["description"]
    row.prompt = default["prompt"]
    if changed:
        row.version = (row.version or 1) + 1
    row.updated_by = updated_by
    await db.commit()
    await db.refresh(row)
    return row
