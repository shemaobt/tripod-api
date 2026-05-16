from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.translation_helper import THAgentPrompt


async def list_agent_prompts(db: AsyncSession) -> list[THAgentPrompt]:
    stmt = select(THAgentPrompt).order_by(THAgentPrompt.agent_id.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())
