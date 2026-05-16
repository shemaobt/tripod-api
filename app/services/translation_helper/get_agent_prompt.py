from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.translation_helper import AgentId, THAgentPrompt
from app.services.translation_helper._default_prompts import get_default_prompt


async def get_agent_prompt(db: AsyncSession, agent_id: AgentId) -> THAgentPrompt:
    stmt = select(THAgentPrompt).where(THAgentPrompt.agent_id == str(agent_id))
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError(f"Agent prompt {agent_id} not found")
    return row


async def get_system_prompt_text(db: AsyncSession, agent_id: AgentId) -> str:
    """Return DB-stored prompt body if present, else baked-in default."""
    stmt = select(THAgentPrompt.prompt).where(THAgentPrompt.agent_id == str(agent_id))
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is not None:
        return row
    return get_default_prompt(agent_id)["prompt"]
