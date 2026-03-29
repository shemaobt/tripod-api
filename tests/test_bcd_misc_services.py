import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.services.book_context.create_bcd import create_bcd
from app.services.book_context.create_new_version import create_new_version
from app.services.book_context.list_generation_logs import list_generation_logs
from app.services.book_context.track_step import track_step
from app.services.book_context.update_section import update_section
from tests.baker import make_bcd, make_bible_book, make_user


@pytest.mark.asyncio
async def test_create_bcd_stores_genre_context(db_session):
    user = await make_user(db_session, email="genre1@test.com")
    book = await make_bible_book(
        db_session,
        name="Ruth",
        abbreviation="Rth",
        order=8,
        chapter_count=4,
    )

    bcd = await create_bcd(db_session, book.id, user.id, "poetry")

    assert bcd.genre_context == {"primary_genre": "poetry"}


@pytest.mark.asyncio
async def test_create_bcd_increments_version(db_session):
    user = await make_user(db_session, email="ver1@test.com")
    book = await make_bible_book(
        db_session,
        name="Ruth",
        abbreviation="Rth",
        order=8,
        chapter_count=4,
    )

    bcd1 = await create_bcd(db_session, book.id, user.id, "narrative")
    bcd2 = await create_bcd(db_session, book.id, user.id, "narrative")

    assert bcd1.version == 1
    assert bcd2.version == 2


@pytest.mark.asyncio
async def test_update_section_unknown_key_raises_not_found(db_session):
    user = await make_user(db_session, email="unk1@test.com")
    book = await make_bible_book(
        db_session,
        name="Ruth",
        abbreviation="Rth",
        order=8,
        chapter_count=4,
    )
    bcd = await make_bcd(db_session, book.id, user.id)

    with pytest.raises(NotFoundError, match="Unknown section"):
        await update_section(db_session, bcd.id, "nonexistent_section", {}, user.id)


@pytest.mark.asyncio
async def test_update_section_rejects_generating(db_session):
    user = await make_user(db_session, email="gen2@test.com")
    book = await make_bible_book(
        db_session,
        name="Ruth",
        abbreviation="Rth",
        order=8,
        chapter_count=4,
    )
    bcd = await make_bcd(db_session, book.id, user.id, status="generating")

    with pytest.raises(ConflictError, match="currently being generated"):
        await update_section(db_session, bcd.id, "places", [], user.id)


@pytest.mark.asyncio
async def test_create_new_version_rejects_draft(db_session):
    user = await make_user(db_session, email="nv1@test.com")
    book = await make_bible_book(
        db_session,
        name="Ruth",
        abbreviation="Rth",
        order=8,
        chapter_count=4,
    )
    bcd = await make_bcd(db_session, book.id, user.id, status="draft")

    with pytest.raises(ConflictError, match="approved document"):
        await create_new_version(db_session, bcd.id, user.id)


@pytest.mark.asyncio
async def test_track_step_success(db_session):
    user = await make_user(db_session, email="ts1@test.com")
    book = await make_bible_book(
        db_session,
        name="Ruth",
        abbreviation="Rth",
        order=8,
        chapter_count=4,
    )
    bcd = await make_bcd(db_session, book.id, user.id)

    async with track_step(db_session, bcd.id, "structural_outline", 1, input_summary="test") as log:
        log.output_summary = "done"

    assert log.status == "completed"
    assert log.duration_ms is not None
    assert log.completed_at is not None


@pytest.mark.asyncio
async def test_track_step_failure(db_session):
    user = await make_user(db_session, email="ts2@test.com")
    book = await make_bible_book(
        db_session,
        name="Ruth",
        abbreviation="Rth",
        order=8,
        chapter_count=4,
    )
    bcd = await make_bcd(db_session, book.id, user.id)

    with pytest.raises(RuntimeError, match="boom"):
        async with track_step(db_session, bcd.id, "participants", 2) as log:
            raise RuntimeError("boom")

    assert log.status == "failed"
    assert "boom" in log.error_detail


@pytest.mark.asyncio
async def test_list_generation_logs_ordered(db_session):
    user = await make_user(db_session, email="lg1@test.com")
    book = await make_bible_book(
        db_session,
        name="Ruth",
        abbreviation="Rth",
        order=8,
        chapter_count=4,
    )
    bcd = await make_bcd(db_session, book.id, user.id)

    async with track_step(db_session, bcd.id, "collect_bhsa", 0):
        pass
    async with track_step(db_session, bcd.id, "structural_outline", 1):
        pass
    async with track_step(db_session, bcd.id, "participants", 2):
        pass

    logs = await list_generation_logs(db_session, bcd.id)
    assert len(logs) == 3
    assert [log_entry.step_name for log_entry in logs] == [
        "collect_bhsa",
        "structural_outline",
        "participants",
    ]
