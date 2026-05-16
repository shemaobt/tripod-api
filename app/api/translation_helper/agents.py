from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.translation_helper._deps import th_access
from app.core.database import get_db
from app.db.models.translation_helper import AgentId
from app.models.translation_helper import AgentInfoResponse
from app.services import translation_helper_service as th_service
from app.services.translation_helper._default_prompts import get_default_prompt
from app.services.translation_helper.agents_catalog import AGENT_CATALOG

router = APIRouter()


@router.get("/agents", response_model=list[AgentInfoResponse], dependencies=[th_access])
async def list_agents(db: AsyncSession = Depends(get_db)) -> list[AgentInfoResponse]:
    rows = await th_service.list_agent_prompts(db)
    by_id = {row.agent_id: row for row in rows}
    result: list[AgentInfoResponse] = []
    for agent_id, catalog in AGENT_CATALOG.items():
        db_row = by_id.get(str(agent_id))
        if db_row is not None:
            name = db_row.name
            description = db_row.description
            prompt_version: int | None = db_row.version
        else:
            default = get_default_prompt(agent_id)
            name = default["name"]
            description = default["description"]
            prompt_version = None
        result.append(
            AgentInfoResponse(
                id=AgentId(str(agent_id)),
                name=name,
                description=description,
                short=str(catalog["short"]),
                icon=str(catalog["icon"]),
                starters=list(catalog["starters"]),  # type: ignore[arg-type]
                prompt_version=prompt_version,
            )
        )
    return result
