import pytest

from app.core.exceptions import AuthorizationError, ConflictError
from app.services.book_context.approve_bcd import approve_bcd
from app.services.book_context.request_revision import request_revision
from tests.baker import make_bcd, make_bible_book, make_user


@pytest.mark.asyncio
async def test_admin_approval_auto_approves(db_session):
    user = await make_user(db_session, email="admin1@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, user.id, status="draft")

    result = await approve_bcd(db_session, bcd.id, user.id, ["admin"])
    assert result.status.value == "approved"


@pytest.mark.asyncio
async def test_single_facilitator_sets_review(db_session):
    user = await make_user(db_session, email="fac1@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, user.id, status="draft")

    result = await approve_bcd(db_session, bcd.id, user.id, ["facilitator"])
    assert result.status.value == "review"


@pytest.mark.asyncio
async def test_two_facilitators_without_specialist_stay_review(db_session):
    fac1 = await make_user(db_session, email="fac2a@test.com")
    fac2 = await make_user(db_session, email="fac2b@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, fac1.id, status="draft")

    await approve_bcd(db_session, bcd.id, fac1.id, ["facilitator"])
    result = await approve_bcd(db_session, bcd.id, fac2.id, ["facilitator"])
    assert result.status.value == "review"


@pytest.mark.asyncio
async def test_duplicate_approval_rejected(db_session):
    user = await make_user(db_session, email="dup1@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, user.id, status="draft")

    await approve_bcd(db_session, bcd.id, user.id, ["facilitator"])
    with pytest.raises(ConflictError, match="already approved"):
        await approve_bcd(db_session, bcd.id, user.id, ["facilitator"])


@pytest.mark.asyncio
async def test_approval_rejects_unauthorized_role(db_session):
    user = await make_user(db_session, email="analyst1@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, user.id, status="draft")

    with pytest.raises(AuthorizationError, match="admin, facilitator, or specialist"):
        await approve_bcd(db_session, bcd.id, user.id, ["analyst"])


@pytest.mark.asyncio
async def test_approval_rejects_already_approved(db_session):
    user = await make_user(db_session, email="appr1@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, user.id, status="approved")

    with pytest.raises(ConflictError, match="already approved"):
        await approve_bcd(db_session, bcd.id, user.id, ["admin"])


@pytest.mark.asyncio
async def test_approval_rejects_generating(db_session):
    user = await make_user(db_session, email="gen1@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, user.id, status="generating")

    with pytest.raises(ConflictError, match="Only draft or in-review"):
        await approve_bcd(db_session, bcd.id, user.id, ["admin"])


@pytest.mark.asyncio
async def test_request_revision_resets_to_draft(db_session):
    user = await make_user(db_session, email="rev1@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, user.id, status="review")

    result = await request_revision(db_session, bcd.id, user.id, "facilitator")
    assert result.status.value == "draft"


@pytest.mark.asyncio
async def test_request_revision_rejects_generating(db_session):
    user = await make_user(db_session, email="rev2@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, user.id, status="generating")

    with pytest.raises(ConflictError, match="being generated"):
        await request_revision(db_session, bcd.id, user.id, "admin")


@pytest.mark.asyncio
async def test_request_revision_rejects_unauthorized_role(db_session):
    user = await make_user(db_session, email="rev3@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, user.id, status="draft")

    with pytest.raises(AuthorizationError, match="Only admins and facilitators"):
        await request_revision(db_session, bcd.id, user.id, "viewer")
