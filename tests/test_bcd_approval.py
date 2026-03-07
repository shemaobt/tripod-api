import pytest

from app.core.exceptions import AuthorizationError, ConflictError
from app.services.book_context.approve_bcd import approve_bcd
from app.services.book_context.request_revision import request_revision
from tests.baker import make_bcd, make_bible_book, make_user


@pytest.mark.asyncio
async def test_single_admin_approves_immediately(db_session):
    admin = await make_user(db_session, email="admin@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, admin.id)

    result = await approve_bcd(db_session, bcd.id, admin.id, ["admin"])

    assert result.status.value == "approved"


@pytest.mark.asyncio
async def test_single_facilitator_moves_to_review(db_session):
    user = await make_user(db_session, email="fac1@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, user.id)

    result = await approve_bcd(db_session, bcd.id, user.id, ["facilitator"])

    assert result.status.value == "review"


@pytest.mark.asyncio
async def test_two_facilitators_without_specialist_stay_review(db_session):
    fac1 = await make_user(db_session, email="fac2a@test.com")
    fac2 = await make_user(db_session, email="fac2b@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, fac1.id)

    await approve_bcd(db_session, bcd.id, fac1.id, ["facilitator"])
    result = await approve_bcd(db_session, bcd.id, fac2.id, ["facilitator"])

    assert result.status.value == "review"


@pytest.mark.asyncio
async def test_facilitator_then_admin_approves(db_session):
    fac = await make_user(db_session, email="fac3@test.com")
    admin = await make_user(db_session, email="admin3@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, fac.id)

    await approve_bcd(db_session, bcd.id, fac.id, ["facilitator"])
    result = await approve_bcd(db_session, bcd.id, admin.id, ["admin"])

    assert result.status.value == "approved"


@pytest.mark.asyncio
async def test_admin_then_facilitator_already_approved(db_session):
    admin = await make_user(db_session, email="admin4@test.com")
    fac = await make_user(db_session, email="fac4@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, admin.id)

    result = await approve_bcd(db_session, bcd.id, admin.id, ["admin"])
    assert result.status.value == "approved"

    with pytest.raises(ConflictError, match="already approved"):
        await approve_bcd(db_session, bcd.id, fac.id, ["facilitator"])


@pytest.mark.asyncio
async def test_rejects_duplicate_approval(db_session):
    fac = await make_user(db_session, email="fac5@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, fac.id)

    await approve_bcd(db_session, bcd.id, fac.id, ["facilitator"])

    with pytest.raises(ConflictError, match="already approved this document"):
        await approve_bcd(db_session, bcd.id, fac.id, ["facilitator"])


@pytest.mark.asyncio
async def test_rejects_non_facilitator_non_admin(db_session):
    user = await make_user(db_session, email="annotator@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, user.id)

    with pytest.raises(AuthorizationError, match="admin, facilitator, or specialist"):
        await approve_bcd(db_session, bcd.id, user.id, ["annotator"])


@pytest.mark.asyncio
async def test_rejects_if_generating(db_session):
    user = await make_user(db_session, email="fac6@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, user.id, status="generating")

    with pytest.raises(ConflictError, match="Only draft or in-review"):
        await approve_bcd(db_session, bcd.id, user.id, ["admin"])


@pytest.mark.asyncio
async def test_request_revision_clears_approvals(db_session):
    fac = await make_user(db_session, email="fac7@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, fac.id, status="review")

    result = await request_revision(db_session, bcd.id, fac.id, "facilitator")

    assert result.status.value == "draft"


@pytest.mark.asyncio
async def test_request_revision_from_approved(db_session):
    admin = await make_user(db_session, email="admin8@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, admin.id, status="approved")

    result = await request_revision(db_session, bcd.id, admin.id, "admin")

    assert result.status.value == "draft"


@pytest.mark.asyncio
async def test_request_revision_rejects_non_facilitator(db_session):
    user = await make_user(db_session, email="annotator2@test.com")
    book = await make_bible_book(db_session, name="Ruth", abbreviation="Rth", order=8, chapter_count=4)
    bcd = await make_bcd(db_session, book.id, user.id, status="review")

    with pytest.raises(AuthorizationError, match="Only admins and facilitators"):
        await request_revision(db_session, bcd.id, user.id, "annotator")
