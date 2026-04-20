from datetime import UTC, datetime

import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.db.models.oc_recording import OC_Recording
from app.db.models.oc_storyteller import OC_Storyteller
from app.db.models.project import ProjectUserAccess
from app.models.oc_storyteller import StorytellerCreate, StorytellerUpdate
from tests.baker import make_language, make_project, make_user


async def _seed_project_with_manager(db: AsyncSession) -> tuple[str, str]:
    lang = await make_language(db)
    project = await make_project(db, lang.id)
    manager = await make_user(db, email="pm@test.com")
    access = ProjectUserAccess(project_id=project.id, user_id=manager.id, role="manager")
    db.add(access)
    await db.commit()
    return project.id, manager.id


def _import_service():
    from app.services.oral_collector import storyteller_service

    return storyteller_service


@pytest.mark.asyncio
async def test_create_storyteller_as_manager(db_session: AsyncSession) -> None:
    ss = _import_service()
    project_id, manager_id = await _seed_project_with_manager(db_session)

    data = StorytellerCreate(
        name="Ana",
        sex="female",
        age=62,
        location="Alto Xingu",
        external_acceptance_confirmed=True,
    )
    st = await ss.create_storyteller(db_session, project_id, data, manager_id)

    assert st.id is not None
    assert st.project_id == project_id
    assert st.name == "Ana"
    assert st.sex == "female"
    assert st.age == 62
    assert st.external_acceptance_confirmed is True
    assert st.external_acceptance_confirmed_at is not None
    assert st.external_acceptance_confirmed_by == manager_id


@pytest.mark.asyncio
async def test_create_storyteller_non_manager_blocked(db_session: AsyncSession) -> None:
    ss = _import_service()
    project_id, _ = await _seed_project_with_manager(db_session)
    outsider = await make_user(db_session, email="outsider@test.com")

    data = StorytellerCreate(name="Ana", sex="female", external_acceptance_confirmed=True)
    with pytest.raises(AuthorizationError):
        await ss.create_storyteller(db_session, project_id, data, outsider.id)


@pytest.mark.asyncio
async def test_create_storyteller_rejects_unconfirmed_at_schema() -> None:
    with pytest.raises(PydanticValidationError):
        StorytellerCreate(name="Ana", sex="female", external_acceptance_confirmed=False)


@pytest.mark.asyncio
async def test_create_storyteller_service_guards_unconfirmed(
    db_session: AsyncSession,
) -> None:
    ss = _import_service()
    project_id, manager_id = await _seed_project_with_manager(db_session)

    data = StorytellerCreate.model_construct(
        name="Ana",
        sex="female",
        age=None,
        location=None,
        dialect=None,
        external_acceptance_confirmed=False,
    )
    with pytest.raises(ValidationError):
        await ss.create_storyteller(db_session, project_id, data, manager_id)


@pytest.mark.asyncio
async def test_list_project_storytellers_ordered_by_name(
    db_session: AsyncSession,
) -> None:
    ss = _import_service()
    project_id, manager_id = await _seed_project_with_manager(db_session)

    for name in ["Zelda", "Ana", "Marcos"]:
        await ss.create_storyteller(
            db_session,
            project_id,
            StorytellerCreate(name=name, sex="female", external_acceptance_confirmed=True),
            manager_id,
        )

    rows = await ss.list_project_storytellers(db_session, project_id)
    assert [r.name for r in rows] == ["Ana", "Marcos", "Zelda"]


@pytest.mark.asyncio
async def test_update_storyteller_only_by_manager(db_session: AsyncSession) -> None:
    ss = _import_service()
    project_id, manager_id = await _seed_project_with_manager(db_session)
    outsider = await make_user(db_session, email="outsider@test.com")

    st = await ss.create_storyteller(
        db_session,
        project_id,
        StorytellerCreate(name="Ana", sex="female", external_acceptance_confirmed=True),
        manager_id,
    )

    with pytest.raises(AuthorizationError):
        await ss.update_storyteller(
            db_session, st.id, StorytellerUpdate(dialect="Trumai"), outsider.id
        )

    updated = await ss.update_storyteller(
        db_session, st.id, StorytellerUpdate(dialect="Trumai"), manager_id
    )
    assert updated.dialect == "Trumai"
    assert updated.external_acceptance_confirmed_by == manager_id


@pytest.mark.asyncio
async def test_update_storyteller_preserves_audit_fields(
    db_session: AsyncSession,
) -> None:
    ss = _import_service()
    project_id, manager_id = await _seed_project_with_manager(db_session)

    st = await ss.create_storyteller(
        db_session,
        project_id,
        StorytellerCreate(name="Ana", sex="female", external_acceptance_confirmed=True),
        manager_id,
    )
    confirmed_at = st.external_acceptance_confirmed_at
    confirmed_by = st.external_acceptance_confirmed_by

    await ss.update_storyteller(db_session, st.id, StorytellerUpdate(name="Anna"), manager_id)
    refreshed = await ss.get_storyteller(db_session, st.id)
    assert refreshed.name == "Anna"
    assert refreshed.external_acceptance_confirmed_at == confirmed_at
    assert refreshed.external_acceptance_confirmed_by == confirmed_by


@pytest.mark.asyncio
async def test_delete_storyteller_nulls_recording_link(
    db_session: AsyncSession,
) -> None:
    ss = _import_service()
    project_id, manager_id = await _seed_project_with_manager(db_session)

    st = await ss.create_storyteller(
        db_session,
        project_id,
        StorytellerCreate(name="Ana", sex="female", external_acceptance_confirmed=True),
        manager_id,
    )

    from app.db.models.oc_genre import OC_Genre, OC_Subcategory

    genre = OC_Genre(name="narrative", sort_order=0)
    db_session.add(genre)
    await db_session.flush()
    sub = OC_Subcategory(genre_id=genre.id, name="folktale", sort_order=0)
    db_session.add(sub)
    await db_session.commit()

    rec = OC_Recording(
        project_id=project_id,
        genre_id=genre.id,
        subcategory_id=sub.id,
        storyteller_id=st.id,
        user_id=manager_id,
        title="test",
        duration_seconds=10.0,
        file_size_bytes=1024,
        format="m4a",
        recorded_at=datetime.now(UTC),
    )
    db_session.add(rec)
    await db_session.commit()
    await db_session.refresh(rec)
    assert rec.storyteller_id == st.id

    await ss.delete_storyteller(db_session, st.id, manager_id)

    await db_session.refresh(rec)
    assert rec.storyteller_id is None

    stmt2 = select(OC_Storyteller).where(OC_Storyteller.id == st.id)
    result2 = await db_session.execute(stmt2)
    assert result2.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_get_storyteller_not_found(db_session: AsyncSession) -> None:
    ss = _import_service()
    with pytest.raises(NotFoundError):
        await ss.get_storyteller(db_session, "does-not-exist")
