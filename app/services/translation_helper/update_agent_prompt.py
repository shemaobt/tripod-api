from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.translation_helper import AgentId, THAgentPrompt
from app.services.translation_helper.get_agent_prompt import get_agent_prompt


async def update_agent_prompt(
    db: AsyncSession,
    agent_id: AgentId,
    *,
    updated_by: str,
    name: str | None = None,
    description: str | None = None,
    prompt: str | None = None,
) -> THAgentPrompt:
    row = await get_agent_prompt(db, agent_id)
    if name is not None:
        row.name = name
    if description is not None:
        row.description = description
    if prompt is not None and prompt != row.prompt:
        row.prompt = prompt
        row.version = (row.version or 1) + 1
    row.updated_by = updated_by
    await db.commit()
    await db.refresh(row)
    return row
