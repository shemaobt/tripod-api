from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.translation_helper import AgentId, THAgentPrompt
from app.services.translation_helper._default_prompts import DEFAULT_PROMPTS


async def seed_agent_prompts(db: AsyncSession) -> int:
    """Insert default prompt rows for any agent that does not yet have one.

    Idempotent and safe under concurrent boots: each insert runs in a
    savepoint; if a parallel replica wins the race, the IntegrityError
    on the unique `agent_id` constraint is swallowed and we move on.
    Returns the number of rows we successfully inserted.
    """
    existing_stmt = select(THAgentPrompt.agent_id)
    result = await db.execute(existing_stmt)
    existing_ids = {row for row in result.scalars().all()}

    inserted = 0
    for agent_id in AgentId:
        if str(agent_id) in existing_ids:
            continue
        default = DEFAULT_PROMPTS[agent_id]
        row = THAgentPrompt(
            agent_id=str(agent_id),
            name=default["name"],
            description=default["description"],
            prompt=default["prompt"],
            version=1,
        )
        try:
            async with db.begin_nested():
                db.add(row)
            inserted += 1
        except IntegrityError:
            continue

    if inserted:
        await db.commit()
    return inserted
