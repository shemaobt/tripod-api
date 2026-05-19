from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.project_health._deps import ph_admin, ph_platform_admin
from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.db.models.auth import User
from app.db.models.project_health import PHAgentPrompt
from app.models.project_health import (
    AgentPromptListResponse,
    AgentPromptResponse,
    AgentPromptUpdateRequest,
)
from app.services.project_health.agents._default_prompts import get_placeholders
from app.services.project_health.prompts import (
    get_prompt_or_404,
    list_prompts,
    reset_prompt,
    update_prompt,
)

router = APIRouter()


def _to_response(row: PHAgentPrompt) -> AgentPromptResponse:
    return AgentPromptResponse(
        id=row.id,
        prompt_key=row.prompt_key,
        name=row.name,
        description=row.description,
        template=row.template,
        placeholders=list(get_placeholders(row.prompt_key)),
        version=row.version,
        updated_by=row.updated_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get(
    "/admin/prompts",
    response_model=AgentPromptListResponse,
    dependencies=[ph_admin],
)
async def admin_list_prompts_endpoint(
    db: AsyncSession = Depends(get_db),
) -> AgentPromptListResponse:
    rows = await list_prompts(db)
    return AgentPromptListResponse(prompts=[_to_response(r) for r in rows])


@router.get(
    "/admin/prompts/{prompt_key}",
    response_model=AgentPromptResponse,
    dependencies=[ph_admin],
)
async def admin_get_prompt_endpoint(
    prompt_key: str,
    db: AsyncSession = Depends(get_db),
) -> AgentPromptResponse:
    row = await get_prompt_or_404(db, prompt_key)
    return _to_response(row)


@router.put(
    "/admin/prompts/{prompt_key}",
    response_model=AgentPromptResponse,
    dependencies=[ph_platform_admin],
)
async def admin_update_prompt_endpoint(
    prompt_key: str,
    payload: AgentPromptUpdateRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> AgentPromptResponse:
    row = await update_prompt(
        db,
        prompt_key,
        updated_by=actor.id,
        name=payload.name,
        description=payload.description,
        template=payload.template,
    )
    return _to_response(row)


@router.post(
    "/admin/prompts/{prompt_key}/reset",
    response_model=AgentPromptResponse,
    dependencies=[ph_platform_admin],
)
async def admin_reset_prompt_endpoint(
    prompt_key: str,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> AgentPromptResponse:
    row = await reset_prompt(db, prompt_key, updated_by=actor.id)
    return _to_response(row)
