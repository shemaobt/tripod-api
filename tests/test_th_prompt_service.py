import pytest
from sqlalchemy import select

from app.core.exceptions import NotFoundError
from app.db.models.translation_helper import AgentId, THAgentPrompt
from app.services.translation_helper._default_prompts import DEFAULT_PROMPTS
from app.services.translation_helper.get_agent_prompt import (
    get_agent_prompt,
    get_system_prompt_text,
)
from app.services.translation_helper.list_agent_prompts import list_agent_prompts
from app.services.translation_helper.reset_agent_prompt import (
    reset_agent_prompt_to_default,
)
from app.services.translation_helper.seed_agent_prompts import seed_agent_prompts
from app.services.translation_helper.update_agent_prompt import update_agent_prompt
from tests.baker import make_user


@pytest.mark.asyncio
async def test_seed_agent_prompts_inserts_five(db_session) -> None:
    inserted = await seed_agent_prompts(db_session)
    assert inserted == 5
    rows = (await db_session.execute(select(THAgentPrompt))).scalars().all()
    assert {r.agent_id for r in rows} == {str(a) for a in AgentId}


@pytest.mark.asyncio
async def test_seed_agent_prompts_is_idempotent(db_session) -> None:
    first = await seed_agent_prompts(db_session)
    second = await seed_agent_prompts(db_session)
    assert first == 5
    assert second == 0
    count = (await db_session.execute(select(THAgentPrompt))).scalars().all()
    assert len(count) == 5


@pytest.mark.asyncio
async def test_get_agent_prompt_returns_seeded(db_session) -> None:
    await seed_agent_prompts(db_session)
    row = await get_agent_prompt(db_session, AgentId.STORYTELLER)
    assert row.agent_id == str(AgentId.STORYTELLER)
    assert row.prompt == DEFAULT_PROMPTS[AgentId.STORYTELLER]["prompt"]


@pytest.mark.asyncio
async def test_get_agent_prompt_raises_when_missing(db_session) -> None:
    with pytest.raises(NotFoundError, match=r"Agent prompt .* not found"):
        await get_agent_prompt(db_session, AgentId.STORYTELLER)


@pytest.mark.asyncio
async def test_list_agent_prompts_returns_all_seeded(db_session) -> None:
    await seed_agent_prompts(db_session)
    rows = await list_agent_prompts(db_session)
    assert len(rows) == 5


@pytest.mark.asyncio
async def test_update_agent_prompt_bumps_version_when_prompt_changes(db_session) -> None:
    await seed_agent_prompts(db_session)
    admin = await make_user(db_session, email="th_admin@test.com", is_platform_admin=True)
    updated = await update_agent_prompt(
        db_session,
        AgentId.STORYTELLER,
        updated_by=admin.id,
        prompt="new prompt body",
    )
    assert updated.prompt == "new prompt body"
    assert updated.version == 2
    assert updated.updated_by == admin.id


@pytest.mark.asyncio
async def test_update_agent_prompt_no_bump_when_only_metadata(db_session) -> None:
    await seed_agent_prompts(db_session)
    admin = await make_user(db_session, email="th_admin2@test.com", is_platform_admin=True)
    updated = await update_agent_prompt(
        db_session,
        AgentId.STORYTELLER,
        updated_by=admin.id,
        name="Renamed",
    )
    assert updated.name == "Renamed"
    assert updated.version == 1


@pytest.mark.asyncio
async def test_reset_agent_prompt_restores_default_and_bumps_version(db_session) -> None:
    await seed_agent_prompts(db_session)
    admin = await make_user(db_session, email="th_admin3@test.com", is_platform_admin=True)
    await update_agent_prompt(
        db_session, AgentId.STORYTELLER, updated_by=admin.id, prompt="custom"
    )

    reset = await reset_agent_prompt_to_default(
        db_session, AgentId.STORYTELLER, updated_by=admin.id
    )
    assert reset.prompt == DEFAULT_PROMPTS[AgentId.STORYTELLER]["prompt"]
    assert reset.version == 3


@pytest.mark.asyncio
async def test_get_system_prompt_text_falls_back_to_default(db_session) -> None:
    text = await get_system_prompt_text(db_session, AgentId.STORYTELLER)
    assert text == DEFAULT_PROMPTS[AgentId.STORYTELLER]["prompt"]


@pytest.mark.asyncio
async def test_get_system_prompt_text_prefers_db(db_session) -> None:
    await seed_agent_prompts(db_session)
    admin = await make_user(db_session, email="th_admin4@test.com", is_platform_admin=True)
    await update_agent_prompt(
        db_session, AgentId.STORYTELLER, updated_by=admin.id, prompt="overridden"
    )
    text = await get_system_prompt_text(db_session, AgentId.STORYTELLER)
    assert text == "overridden"
