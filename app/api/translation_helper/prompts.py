from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.translation_helper._deps import th_access
from app.core.auth_middleware import require_platform_admin
from app.core.database import get_db
from app.db.models.auth import User
from app.db.models.translation_helper import AgentId
from app.models.translation_helper import AgentPromptResponse, AgentPromptUpdate
from app.services import translation_helper_service as th_service

router = APIRouter()


@router.get(
    "/prompts",
    response_model=list[AgentPromptResponse],
    dependencies=[th_access],
)
async def list_prompts(
    db: AsyncSession = Depends(get_db),
) -> list[AgentPromptResponse]:
    rows = await th_service.list_agent_prompts(db)
    return [AgentPromptResponse.model_validate(r) for r in rows]


@router.get(
    "/prompts/{agent_id}",
    response_model=AgentPromptResponse,
    dependencies=[th_access],
)
async def get_prompt(
    agent_id: AgentId,
    db: AsyncSession = Depends(get_db),
) -> AgentPromptResponse:
    row = await th_service.get_agent_prompt(db, agent_id)
    return AgentPromptResponse.model_validate(row)


@router.put(
    "/prompts/{agent_id}",
    response_model=AgentPromptResponse,
)
async def update_prompt(
    agent_id: AgentId,
    payload: AgentPromptUpdate,
    admin: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> AgentPromptResponse:
    row = await th_service.update_agent_prompt(
        db,
        agent_id,
        updated_by=admin.id,
        name=payload.name,
        description=payload.description,
        prompt=payload.prompt,
    )
    return AgentPromptResponse.model_validate(row)


@router.post(
    "/prompts/{agent_id}/reset",
    response_model=AgentPromptResponse,
)
async def reset_prompt(
    agent_id: AgentId,
    admin: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> AgentPromptResponse:
    row = await th_service.reset_agent_prompt_to_default(db, agent_id, updated_by=admin.id)
    return AgentPromptResponse.model_validate(row)
