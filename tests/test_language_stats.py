import pytest

from app.core.exceptions import NotFoundError
from app.services import language_service
from tests.baker import make_language, make_project


@pytest.mark.asyncio
async def test_language_stats_lists_projects(db_session) -> None:
    lang = await make_language(db_session, code="ksa")
    other = await make_language(db_session, code="oth")
    await make_project(db_session, language_id=lang.id, name="P1")
    await make_project(db_session, language_id=lang.id, name="P2")
    await make_project(db_session, language_id=other.id, name="P3")

    projects = await language_service.get_language_stats(db_session, lang.id)
    assert len(projects) == 2
    assert {name for _, name in projects} == {"P1", "P2"}


@pytest.mark.asyncio
async def test_language_stats_empty_when_unused(db_session) -> None:
    lang = await make_language(db_session, code="ksb")
    projects = await language_service.get_language_stats(db_session, lang.id)
    assert projects == []


@pytest.mark.asyncio
async def test_language_stats_missing_raises_not_found(db_session) -> None:
    with pytest.raises(NotFoundError, match=r"Language .* not found"):
        await language_service.get_language_stats(
            db_session, "00000000-0000-0000-0000-000000000000"
        )
