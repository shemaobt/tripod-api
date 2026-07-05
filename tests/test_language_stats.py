import pytest

from app.core.exceptions import NotFoundError
from app.services import language_service
from tests.baker import make_language, make_project


@pytest.mark.asyncio
async def test_language_stats_counts_projects(db_session) -> None:
    lang = await make_language(db_session, code="ksa")
    other = await make_language(db_session, code="oth")
    await make_project(db_session, language_id=lang.id, name="P1")
    await make_project(db_session, language_id=lang.id, name="P2")
    await make_project(db_session, language_id=other.id, name="P3")

    count = await language_service.get_language_stats(db_session, lang.id)
    assert count == 2


@pytest.mark.asyncio
async def test_language_stats_zero_when_unused(db_session) -> None:
    lang = await make_language(db_session, code="ksb")
    count = await language_service.get_language_stats(db_session, lang.id)
    assert count == 0


@pytest.mark.asyncio
async def test_language_stats_missing_raises_not_found(db_session) -> None:
    with pytest.raises(NotFoundError, match=r"Language .* not found"):
        await language_service.get_language_stats(
            db_session, "00000000-0000-0000-0000-000000000000"
        )
