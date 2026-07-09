import pytest

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.services import language_service
from tests.baker import make_language, make_project, make_user


@pytest.mark.asyncio
async def test_create_language(db_session) -> None:
    language = await language_service.create_language(db_session, name="Kokama", code="kos")
    assert language.name == "Kokama"
    assert language.code == "kos"


@pytest.mark.asyncio
async def test_create_language_lowercases_code(db_session) -> None:
    language = await language_service.create_language(db_session, name="Portuguese", code="POR")
    assert language.code == "por"


@pytest.mark.asyncio
async def test_create_language_raises_conflict_when_code_exists(db_session) -> None:
    await make_language(db_session, code="kos")
    with pytest.raises(ConflictError, match="code already exists"):
        await language_service.create_language(db_session, name="Other", code="kos")


@pytest.mark.asyncio
async def test_get_language_by_id(db_session) -> None:
    created = await make_language(db_session, name="Kokama", code="kos")
    language = await language_service.get_language_by_id(db_session, created.id)
    assert language is not None
    assert language.id == created.id
    assert language.code == "kos"


@pytest.mark.asyncio
async def test_get_language_by_id_returns_none_when_missing(db_session) -> None:
    language = await language_service.get_language_by_id(
        db_session, "00000000-0000-0000-0000-000000000000"
    )
    assert language is None


@pytest.mark.asyncio
async def test_get_language_by_code(db_session) -> None:
    await make_language(db_session, name="Kokama", code="kos")
    language = await language_service.get_language_by_code(db_session, "kos")
    assert language is not None
    assert language.code == "kos"


@pytest.mark.asyncio
async def test_get_language_by_code_returns_none_when_missing(db_session) -> None:
    language = await language_service.get_language_by_code(db_session, "xyz")
    assert language is None


@pytest.mark.asyncio
async def test_list_languages_ordered_by_code(db_session) -> None:
    await make_language(db_session, code="zzz", name="Z")
    await make_language(db_session, code="aaa", name="A")
    languages = await language_service.list_languages(db_session)
    assert len(languages) == 2
    assert languages[0].code == "aaa"
    assert languages[1].code == "zzz"


@pytest.mark.asyncio
async def test_create_language_sets_created_by(db_session) -> None:
    user = await make_user(db_session)
    language = await language_service.create_language(
        db_session, name="Kokama", code="kos", created_by=user.id
    )
    assert language.created_by == user.id


@pytest.mark.asyncio
async def test_deactivate_language_sets_inactive(db_session) -> None:
    admin = await make_user(db_session, email="admin@example.com", is_platform_admin=True)
    created = await make_language(db_session, code="kos")
    deactivated = await language_service.deactivate_language(db_session, created.id, admin)
    assert deactivated.is_active is False


@pytest.mark.asyncio
async def test_deactivate_language_by_creator(db_session) -> None:
    creator = await make_user(db_session)
    created = await make_language(db_session, code="kos", created_by=creator.id)
    deactivated = await language_service.deactivate_language(db_session, created.id, creator)
    assert deactivated.is_active is False


@pytest.mark.asyncio
async def test_deactivate_language_forbidden_for_non_creator(db_session) -> None:
    creator = await make_user(db_session, email="creator@example.com")
    other = await make_user(db_session, email="other@example.com")
    created = await make_language(db_session, code="kos", created_by=creator.id)
    with pytest.raises(AuthorizationError, match="languages you created"):
        await language_service.deactivate_language(db_session, created.id, other)


@pytest.mark.asyncio
async def test_deactivate_language_blocked_when_in_use(db_session) -> None:
    admin = await make_user(db_session, email="admin@example.com", is_platform_admin=True)
    created = await make_language(db_session, code="kos")
    await make_project(db_session, created.id, name="Genesis OBT")
    with pytest.raises(ConflictError, match="used by 1 project"):
        await language_service.deactivate_language(db_session, created.id, admin)


@pytest.mark.asyncio
async def test_deactivate_language_missing_raises_not_found(db_session) -> None:
    admin = await make_user(db_session, email="admin@example.com", is_platform_admin=True)
    with pytest.raises(NotFoundError, match=r"Language .* not found"):
        await language_service.deactivate_language(
            db_session, "00000000-0000-0000-0000-000000000000", admin
        )


@pytest.mark.asyncio
async def test_list_languages_hides_inactive_by_default(db_session) -> None:
    admin = await make_user(db_session, email="admin@example.com", is_platform_admin=True)
    active = await make_language(db_session, code="act", name="Active")
    inactive = await make_language(db_session, code="ina", name="Inactive")
    await language_service.deactivate_language(db_session, inactive.id, admin)

    languages = await language_service.list_languages(db_session)
    assert [lang.id for lang in languages] == [active.id]


@pytest.mark.asyncio
async def test_list_languages_include_inactive(db_session) -> None:
    admin = await make_user(db_session, email="admin@example.com", is_platform_admin=True)
    active = await make_language(db_session, code="act", name="Active")
    inactive = await make_language(db_session, code="ina", name="Inactive")
    await language_service.deactivate_language(db_session, inactive.id, admin)

    languages = await language_service.list_languages(db_session, include_inactive=True)
    assert {lang.id for lang in languages} == {active.id, inactive.id}


@pytest.mark.asyncio
async def test_get_language_or_404_raises_when_missing(db_session) -> None:
    with pytest.raises(NotFoundError, match=r"Language .* not found"):
        await language_service.get_language_or_404(
            db_session, "00000000-0000-0000-0000-000000000000"
        )
