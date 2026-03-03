import json
from datetime import UTC, datetime

import pytest

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.services.meaning_map.add_feedback import add_feedback
from app.services.meaning_map.create_meaning_map import create_meaning_map
from app.services.meaning_map.create_pericope import create_pericope
from app.services.meaning_map.delete_meaning_map import delete_meaning_map
from app.services.meaning_map.ensure_ot import ensure_ot
from app.services.meaning_map.export_json import export_json
from app.services.meaning_map.export_prose import export_prose
from app.services.meaning_map.get_book_or_404 import get_book_or_404
from app.services.meaning_map.get_chapter_summaries import get_chapter_summaries
from app.services.meaning_map.get_meaning_map_or_404 import get_meaning_map_or_404
from app.services.meaning_map.get_pericope_or_404 import get_pericope_or_404
from app.services.meaning_map.list_books import list_books
from app.services.meaning_map.list_feedback import list_feedback
from app.services.meaning_map.list_meaning_maps import list_meaning_maps
from app.services.meaning_map.list_pericopes import list_pericopes
from app.services.meaning_map.lock_map import lock_map
from app.services.meaning_map.resolve_feedback import resolve_feedback
from app.services.meaning_map.seed_books import seed_books
from app.services.meaning_map.transition_status import transition_status
from app.services.meaning_map.unlock_map import unlock_map
from app.services.meaning_map.update_meaning_map_data import update_meaning_map_data
from tests.baker import (
    make_bible_book,
    make_meaning_map,
    make_meaning_map_feedback,
    make_pericope,
    make_user,
)

SAMPLE_DATA = {
    "level_1": {"arc": "God creates the heavens and the earth."},
    "level_2_scenes": [
        {
            "scene_number": 1,
            "verses": "1-5",
            "title": "Creation of light",
            "people": [
                {
                    "name": "God",
                    "role": "Creator",
                    "relationship": "",
                    "wants": "to create",
                    "carries": "",
                }
            ],
            "places": [
                {
                    "name": "The void",
                    "role": "setting",
                    "type": "cosmic",
                    "meaning": "emptiness",
                    "effect_on_scene": "sets stage",
                }
            ],
            "objects": [
                {
                    "name": "Light",
                    "what_it_is": "illumination",
                    "function_in_scene": "first creation",
                    "signals": "goodness",
                }
            ],
            "significant_absence": "",
            "what_happens": (
                "God speaks light into existence"
                " and separates it from darkness."
            ),
            "communicative_purpose": (
                "Establishes God as sovereign creator."
                " Shows the power of divine speech."
                " Introduces the pattern of creation by word."
            ),
        }
    ],
    "level_3_propositions": [
        {
            "proposition_number": 1,
            "verse": "1",
            "content": [
                {
                    "question": "What happens?",
                    "answer": "God creates the heavens and the earth.",
                }
            ],
        }
    ],
}


# ---------------------------------------------------------------------------
# CRUD: create_meaning_map, create_pericope, add_feedback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_pericope_success(db_session) -> None:
    book = await make_bible_book(db_session)
    pericope = await create_pericope(
        db_session, book.id, 1, 1, 1, 5, "Gen 1:1-5", title="Creation"
    )
    assert pericope.id
    assert pericope.book_id == book.id
    assert pericope.reference == "Gen 1:1-5"
    assert pericope.title == "Creation"


@pytest.mark.asyncio
async def test_create_meaning_map_success(db_session) -> None:
    user = await make_user(db_session, email="analyst@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await create_meaning_map(db_session, pericope.id, user.id, SAMPLE_DATA)
    assert mm.id
    assert mm.pericope_id == pericope.id
    assert mm.analyst_id == user.id
    assert mm.status == "draft"
    assert mm.data == SAMPLE_DATA


@pytest.mark.asyncio
async def test_create_meaning_map_custom_status(db_session) -> None:
    user = await make_user(db_session, email="analyst2@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await create_meaning_map(
        db_session, pericope.id, user.id, {}, status="cross_check"
    )
    assert mm.status == "cross_check"


@pytest.mark.asyncio
async def test_add_feedback_success(db_session) -> None:
    user = await make_user(db_session, email="analyst3@test.com")
    reviewer = await make_user(db_session, email="reviewer@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id)
    fb = await add_feedback(db_session, mm.id, "level_1.arc", reviewer.id, "Needs work")
    assert fb.id
    assert fb.meaning_map_id == mm.id
    assert fb.section_key == "level_1.arc"
    assert fb.author_id == reviewer.id
    assert fb.content == "Needs work"
    assert fb.resolved is False


@pytest.mark.asyncio
async def test_create_pericope_without_title(db_session) -> None:
    book = await make_bible_book(db_session)
    pericope = await create_pericope(db_session, book.id, 2, 1, 2, 10, "Gen 2:1-10")
    assert pericope.title is None


# ---------------------------------------------------------------------------
# Get-or-404: get_meaning_map_or_404, get_pericope_or_404, get_book_or_404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_book_or_404_success(db_session) -> None:
    book = await make_bible_book(db_session)
    found = await get_book_or_404(db_session, book.id)
    assert found.id == book.id
    assert found.name == "Genesis"


@pytest.mark.asyncio
async def test_get_book_or_404_raises(db_session) -> None:
    with pytest.raises(NotFoundError, match=r"Bible book .* not found"):
        await get_book_or_404(db_session, "nonexistent-id")


@pytest.mark.asyncio
async def test_get_pericope_or_404_success(db_session) -> None:
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    found = await get_pericope_or_404(db_session, pericope.id)
    assert found.id == pericope.id


@pytest.mark.asyncio
async def test_get_pericope_or_404_raises(db_session) -> None:
    with pytest.raises(NotFoundError, match=r"Pericope .* not found"):
        await get_pericope_or_404(db_session, "nonexistent-id")


@pytest.mark.asyncio
async def test_get_meaning_map_or_404_success(db_session) -> None:
    user = await make_user(db_session, email="analyst4@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id)
    found = await get_meaning_map_or_404(db_session, mm.id)
    assert found.id == mm.id


@pytest.mark.asyncio
async def test_get_meaning_map_or_404_raises(db_session) -> None:
    with pytest.raises(NotFoundError, match=r"Meaning map .* not found"):
        await get_meaning_map_or_404(db_session, "nonexistent-id")


# ---------------------------------------------------------------------------
# Lists: list_books, list_meaning_maps, list_feedback, list_pericopes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_books_empty(db_session) -> None:
    result = await list_books(db_session)
    assert result == []


@pytest.mark.asyncio
async def test_list_books_ordered(db_session) -> None:
    await make_bible_book(db_session, name="Exodus", abbreviation="Exod", order=2)
    await make_bible_book(db_session, name="Genesis", abbreviation="Gen", order=1)
    result = await list_books(db_session)
    assert len(result) == 2
    assert result[0].name == "Genesis"
    assert result[1].name == "Exodus"


@pytest.mark.asyncio
async def test_list_meaning_maps_no_filters(db_session) -> None:
    user = await make_user(db_session, email="analyst5@test.com")
    book = await make_bible_book(db_session)
    p1 = await make_pericope(db_session, book.id, reference="Gen 1:1-5")
    p2 = await make_pericope(
        db_session, book.id, chapter_start=2, reference="Gen 2:1-5"
    )
    await make_meaning_map(db_session, p1.id, user.id)
    await make_meaning_map(db_session, p2.id, user.id)
    result = await list_meaning_maps(db_session)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_list_meaning_maps_filter_by_book(db_session) -> None:
    user = await make_user(db_session, email="analyst6@test.com")
    book1 = await make_bible_book(db_session, name="Genesis", abbreviation="Gen", order=1)
    book2 = await make_bible_book(
        db_session, name="Exodus", abbreviation="Exod", order=2
    )
    p1 = await make_pericope(db_session, book1.id, reference="Gen 1:1-5")
    p2 = await make_pericope(db_session, book2.id, reference="Exod 1:1-5")
    await make_meaning_map(db_session, p1.id, user.id)
    await make_meaning_map(db_session, p2.id, user.id)
    result = await list_meaning_maps(db_session, book_id=book1.id)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_list_meaning_maps_filter_by_chapter(db_session) -> None:
    user = await make_user(db_session, email="analyst7@test.com")
    book = await make_bible_book(db_session)
    p1 = await make_pericope(
        db_session, book.id, chapter_start=1, reference="Gen 1:1-5"
    )
    p2 = await make_pericope(
        db_session, book.id, chapter_start=3, reference="Gen 3:1-5"
    )
    await make_meaning_map(db_session, p1.id, user.id)
    await make_meaning_map(db_session, p2.id, user.id)
    result = await list_meaning_maps(db_session, chapter=1)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_list_meaning_maps_filter_by_status(db_session) -> None:
    user = await make_user(db_session, email="analyst8@test.com")
    book = await make_bible_book(db_session)
    p1 = await make_pericope(db_session, book.id, reference="Gen 1:1-5")
    p2 = await make_pericope(
        db_session, book.id, chapter_start=2, reference="Gen 2:1-5"
    )
    await make_meaning_map(db_session, p1.id, user.id, status="draft")
    await make_meaning_map(db_session, p2.id, user.id, status="cross_check")
    result = await list_meaning_maps(db_session, status="draft")
    assert len(result) == 1
    assert result[0].status == "draft"


@pytest.mark.asyncio
async def test_list_meaning_maps_empty(db_session) -> None:
    result = await list_meaning_maps(db_session)
    assert result == []


@pytest.mark.asyncio
async def test_list_feedback_returns_ordered(db_session) -> None:
    user = await make_user(db_session, email="analyst9@test.com")
    reviewer = await make_user(db_session, email="reviewer2@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id)
    await make_meaning_map_feedback(
        db_session, mm.id, reviewer.id, section_key="level_1.arc", content="First"
    )
    await make_meaning_map_feedback(
        db_session, mm.id, reviewer.id, section_key="level_2", content="Second"
    )
    result = await list_feedback(db_session, mm.id)
    assert len(result) == 2
    assert result[0].content == "First"
    assert result[1].content == "Second"


@pytest.mark.asyncio
async def test_list_feedback_empty(db_session) -> None:
    user = await make_user(db_session, email="analyst10@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id)
    result = await list_feedback(db_session, mm.id)
    assert result == []


@pytest.mark.asyncio
async def test_list_pericopes_returns_all_for_book(db_session) -> None:
    book = await make_bible_book(db_session)
    await make_pericope(db_session, book.id, chapter_start=1, reference="Gen 1:1-5")
    await make_pericope(db_session, book.id, chapter_start=2, reference="Gen 2:1-5")
    result = await list_pericopes(db_session, book.id)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_list_pericopes_filter_by_chapter(db_session) -> None:
    book = await make_bible_book(db_session)
    await make_pericope(db_session, book.id, chapter_start=1, chapter_end=1, reference="Gen 1:1-5")
    await make_pericope(db_session, book.id, chapter_start=3, chapter_end=3, reference="Gen 3:1-5")
    result = await list_pericopes(db_session, book.id, chapter=1)
    assert len(result) == 1
    assert result[0].reference == "Gen 1:1-5"


@pytest.mark.asyncio
async def test_list_pericopes_includes_meaning_map_info(db_session) -> None:
    user = await make_user(db_session, email="analyst12@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id, reference="Gen 1:1-5")
    mm = await make_meaning_map(db_session, pericope.id, user.id)
    result = await list_pericopes(db_session, book.id)
    assert len(result) == 1
    assert result[0].meaning_map_id == mm.id
    assert result[0].status == "draft"


@pytest.mark.asyncio
async def test_list_pericopes_without_meaning_map(db_session) -> None:
    book = await make_bible_book(db_session)
    await make_pericope(db_session, book.id, reference="Gen 1:1-5")
    result = await list_pericopes(db_session, book.id)
    assert len(result) == 1
    assert result[0].meaning_map_id is None


# ---------------------------------------------------------------------------
# Delete: delete_meaning_map
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_meaning_map_success(db_session) -> None:
    user = await make_user(db_session, email="analyst13@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id)
    await delete_meaning_map(db_session, mm, user.id)
    with pytest.raises(NotFoundError):
        await get_meaning_map_or_404(db_session, mm.id)


@pytest.mark.asyncio
async def test_delete_meaning_map_raises_if_not_draft(db_session) -> None:
    user = await make_user(db_session, email="analyst14@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session, pericope.id, user.id, status="cross_check"
    )
    with pytest.raises(AuthorizationError, match="Only draft meaning maps can be deleted"):
        await delete_meaning_map(db_session, mm, user.id)


@pytest.mark.asyncio
async def test_delete_meaning_map_raises_if_not_analyst(db_session) -> None:
    analyst = await make_user(db_session, email="analyst15@test.com")
    other = await make_user(db_session, email="other@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, analyst.id)
    with pytest.raises(
        AuthorizationError, match="Only the analyst who created the map can delete it"
    ):
        await delete_meaning_map(db_session, mm, other.id)


# ---------------------------------------------------------------------------
# Update: update_meaning_map_data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_meaning_map_data_success(db_session) -> None:
    user = await make_user(db_session, email="analyst16@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id)
    updated = await update_meaning_map_data(db_session, mm, SAMPLE_DATA, user.id)
    assert updated.data == SAMPLE_DATA


@pytest.mark.asyncio
async def test_update_meaning_map_data_by_lock_holder(db_session) -> None:
    user = await make_user(db_session, email="analyst17@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session, pericope.id, user.id, locked_by=user.id, locked_at=datetime.now(UTC)
    )
    updated = await update_meaning_map_data(db_session, mm, {"new": "data"}, user.id)
    assert updated.data == {"new": "data"}


@pytest.mark.asyncio
async def test_update_meaning_map_data_raises_if_locked_by_other(db_session) -> None:
    analyst = await make_user(db_session, email="analyst18@test.com")
    other = await make_user(db_session, email="other2@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session, pericope.id, analyst.id, locked_by=other.id, locked_at=datetime.now(UTC)
    )
    with pytest.raises(AuthorizationError, match="locked by another user"):
        await update_meaning_map_data(db_session, mm, {"x": 1}, analyst.id)


@pytest.mark.asyncio
async def test_update_meaning_map_data_raises_if_approved(db_session) -> None:
    user = await make_user(db_session, email="analyst19@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session, pericope.id, user.id, status="approved"
    )
    with pytest.raises(AuthorizationError, match="Cannot edit an approved meaning map"):
        await update_meaning_map_data(db_session, mm, {"x": 1}, user.id)


@pytest.mark.asyncio
async def test_update_meaning_map_data_unlocked_map(db_session) -> None:
    user = await make_user(db_session, email="analyst20@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id, data={"old": "data"})
    updated = await update_meaning_map_data(
        db_session, mm, {"replaced": True}, user.id
    )
    assert updated.data == {"replaced": True}


# ---------------------------------------------------------------------------
# Status transitions: transition_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transition_draft_to_cross_check(db_session) -> None:
    user = await make_user(db_session, email="analyst21@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session, pericope.id, user.id, locked_by=user.id, locked_at=datetime.now(UTC)
    )
    result = await transition_status(db_session, mm, "cross_check", user.id)
    assert result.status == "cross_check"
    assert result.locked_by is None
    assert result.locked_at is None


@pytest.mark.asyncio
async def test_transition_cross_check_to_approved(db_session) -> None:
    user = await make_user(db_session, email="analyst22@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session, pericope.id, user.id, status="cross_check"
    )
    result = await transition_status(db_session, mm, "approved", user.id)
    assert result.status == "approved"
    assert result.date_approved is not None
    assert result.approved_by == user.id
    assert result.cross_checker_id == user.id
    assert result.locked_by is None


@pytest.mark.asyncio
async def test_transition_cross_check_to_draft(db_session) -> None:
    user = await make_user(db_session, email="analyst23@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session, pericope.id, user.id, status="cross_check"
    )
    result = await transition_status(db_session, mm, "draft", user.id)
    assert result.status == "draft"
    assert result.locked_by is None


@pytest.mark.asyncio
async def test_transition_invalid_draft_to_approved(db_session) -> None:
    user = await make_user(db_session, email="analyst24@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id)
    with pytest.raises(ConflictError, match="Invalid status transition: draft -> approved"):
        await transition_status(db_session, mm, "approved", user.id)


@pytest.mark.asyncio
async def test_transition_approved_to_draft_invalid(db_session) -> None:
    user = await make_user(db_session, email="analyst25@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session, pericope.id, user.id, status="approved"
    )
    with pytest.raises(ConflictError, match="Invalid status transition: approved -> draft"):
        await transition_status(db_session, mm, "draft", user.id)


@pytest.mark.asyncio
async def test_transition_approved_to_cross_check_invalid(db_session) -> None:
    user = await make_user(db_session, email="analyst26@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session, pericope.id, user.id, status="approved"
    )
    with pytest.raises(
        ConflictError, match="Invalid status transition: approved -> cross_check"
    ):
        await transition_status(db_session, mm, "cross_check", user.id)


@pytest.mark.asyncio
async def test_transition_raises_if_locked_by_other(db_session) -> None:
    analyst = await make_user(db_session, email="analyst27@test.com")
    other = await make_user(db_session, email="other3@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session,
        pericope.id,
        analyst.id,
        locked_by=other.id,
        locked_at=datetime.now(UTC),
    )
    with pytest.raises(AuthorizationError, match="locked by another user"):
        await transition_status(db_session, mm, "cross_check", analyst.id)


@pytest.mark.asyncio
async def test_transition_same_status_invalid(db_session) -> None:
    user = await make_user(db_session, email="analyst28@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id)
    with pytest.raises(ConflictError, match="Invalid status transition: draft -> draft"):
        await transition_status(db_session, mm, "draft", user.id)


@pytest.mark.asyncio
async def test_transition_lock_holder_can_transition(db_session) -> None:
    user = await make_user(db_session, email="analyst29@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session, pericope.id, user.id, locked_by=user.id, locked_at=datetime.now(UTC)
    )
    result = await transition_status(db_session, mm, "cross_check", user.id)
    assert result.status == "cross_check"


@pytest.mark.asyncio
async def test_transition_cross_check_to_approved_clears_lock(db_session) -> None:
    user = await make_user(db_session, email="analyst30@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session,
        pericope.id,
        user.id,
        status="cross_check",
        locked_by=user.id,
        locked_at=datetime.now(UTC),
    )
    result = await transition_status(db_session, mm, "approved", user.id)
    assert result.locked_by is None
    assert result.locked_at is None


# ---------------------------------------------------------------------------
# Locking: lock_map, unlock_map
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lock_map_success(db_session) -> None:
    user = await make_user(db_session, email="analyst31@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id)
    result = await lock_map(db_session, mm, user.id)
    assert result.locked_by == user.id
    assert result.locked_at is not None


@pytest.mark.asyncio
async def test_lock_map_already_locked_by_self(db_session) -> None:
    user = await make_user(db_session, email="analyst32@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session, pericope.id, user.id, locked_by=user.id, locked_at=datetime.now(UTC)
    )
    result = await lock_map(db_session, mm, user.id)
    assert result.locked_by == user.id


@pytest.mark.asyncio
async def test_lock_map_raises_if_locked_by_other(db_session) -> None:
    user1 = await make_user(db_session, email="analyst33@test.com")
    user2 = await make_user(db_session, email="other4@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session, pericope.id, user1.id, locked_by=user1.id, locked_at=datetime.now(UTC)
    )
    with pytest.raises(ConflictError, match="already locked by another user"):
        await lock_map(db_session, mm, user2.id)


@pytest.mark.asyncio
async def test_lock_map_raises_if_approved(db_session) -> None:
    user = await make_user(db_session, email="analyst34@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session, pericope.id, user.id, status="approved"
    )
    with pytest.raises(ConflictError, match="Cannot lock an approved meaning map"):
        await lock_map(db_session, mm, user.id)


@pytest.mark.asyncio
async def test_unlock_map_success(db_session) -> None:
    user = await make_user(db_session, email="analyst35@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session, pericope.id, user.id, locked_by=user.id, locked_at=datetime.now(UTC)
    )
    result = await unlock_map(db_session, mm, user.id)
    assert result.locked_by is None
    assert result.locked_at is None


@pytest.mark.asyncio
async def test_unlock_map_not_locked_returns_unchanged(db_session) -> None:
    user = await make_user(db_session, email="analyst36@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id)
    result = await unlock_map(db_session, mm, user.id)
    assert result.locked_by is None


@pytest.mark.asyncio
async def test_unlock_map_raises_if_locked_by_other_non_admin(db_session) -> None:
    user1 = await make_user(db_session, email="analyst37@test.com")
    user2 = await make_user(db_session, email="other5@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session, pericope.id, user1.id, locked_by=user1.id, locked_at=datetime.now(UTC)
    )
    with pytest.raises(AuthorizationError, match="Only the lock holder or an admin can unlock"):
        await unlock_map(db_session, mm, user2.id)


@pytest.mark.asyncio
async def test_unlock_map_admin_can_unlock_others(db_session) -> None:
    user1 = await make_user(db_session, email="analyst38@test.com")
    admin = await make_user(db_session, email="admin@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session, pericope.id, user1.id, locked_by=user1.id, locked_at=datetime.now(UTC)
    )
    result = await unlock_map(db_session, mm, admin.id, is_admin=True)
    assert result.locked_by is None


@pytest.mark.asyncio
async def test_lock_map_cross_check_status(db_session) -> None:
    user = await make_user(db_session, email="analyst39@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(
        db_session, pericope.id, user.id, status="cross_check"
    )
    result = await lock_map(db_session, mm, user.id)
    assert result.locked_by == user.id


# ---------------------------------------------------------------------------
# Summaries: get_chapter_summaries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_chapter_summaries_empty(db_session) -> None:
    book = await make_bible_book(db_session)
    result = await get_chapter_summaries(db_session, book.id)
    assert result == []


@pytest.mark.asyncio
async def test_get_chapter_summaries_counts_statuses(db_session) -> None:
    user = await make_user(db_session, email="analyst40@test.com")
    book = await make_bible_book(db_session)
    p1 = await make_pericope(
        db_session, book.id, chapter_start=1, chapter_end=1, reference="Gen 1:1-5"
    )
    p2 = await make_pericope(
        db_session, book.id, chapter_start=1, chapter_end=1, reference="Gen 1:6-10"
    )
    await make_meaning_map(db_session, p1.id, user.id, status="draft")
    await make_meaning_map(db_session, p2.id, user.id, status="cross_check")
    result = await get_chapter_summaries(db_session, book.id)
    assert len(result) == 1
    assert result[0].chapter == 1
    assert result[0].pericope_count == 2
    assert result[0].draft_count == 1
    assert result[0].cross_check_count == 1
    assert result[0].approved_count == 0


@pytest.mark.asyncio
async def test_get_chapter_summaries_multi_chapter_pericope(db_session) -> None:
    user = await make_user(db_session, email="analyst41@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(
        db_session, book.id, chapter_start=1, chapter_end=2, reference="Gen 1:1-2:3"
    )
    await make_meaning_map(db_session, pericope.id, user.id, status="draft")
    result = await get_chapter_summaries(db_session, book.id)
    assert len(result) == 2
    assert result[0].chapter == 1
    assert result[0].pericope_count == 1
    assert result[1].chapter == 2
    assert result[1].pericope_count == 1


@pytest.mark.asyncio
async def test_get_chapter_summaries_pericope_without_map(db_session) -> None:
    book = await make_bible_book(db_session)
    await make_pericope(
        db_session, book.id, chapter_start=1, chapter_end=1, reference="Gen 1:1-5"
    )
    result = await get_chapter_summaries(db_session, book.id)
    assert len(result) == 1
    assert result[0].pericope_count == 1
    assert result[0].draft_count == 0


@pytest.mark.asyncio
async def test_get_chapter_summaries_approved_count(db_session) -> None:
    user = await make_user(db_session, email="analyst42@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(
        db_session, book.id, chapter_start=5, chapter_end=5, reference="Gen 5:1-10"
    )
    await make_meaning_map(db_session, pericope.id, user.id, status="approved")
    result = await get_chapter_summaries(db_session, book.id)
    assert len(result) == 1
    assert result[0].chapter == 5
    assert result[0].approved_count == 1


# ---------------------------------------------------------------------------
# Exports: export_json, export_prose
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_json_returns_valid_json(db_session) -> None:
    user = await make_user(db_session, email="analyst43@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id, data=SAMPLE_DATA)
    result = export_json(mm)
    parsed = json.loads(result)
    assert parsed == SAMPLE_DATA


@pytest.mark.asyncio
async def test_export_json_empty_data(db_session) -> None:
    user = await make_user(db_session, email="analyst44@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id, data={})
    result = export_json(mm)
    assert json.loads(result) == {}


@pytest.mark.asyncio
async def test_export_prose_contains_arc(db_session) -> None:
    user = await make_user(db_session, email="analyst45@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id, data=SAMPLE_DATA)
    result = export_prose(mm)
    assert "God creates the heavens and the earth." in result
    assert "# Prose Meaning Map" in result
    assert "Level 1 — The Arc" in result


@pytest.mark.asyncio
async def test_export_prose_contains_scene_details(db_session) -> None:
    user = await make_user(db_session, email="analyst46@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id, data=SAMPLE_DATA)
    result = export_prose(mm)
    assert "Scene 1" in result
    assert "Creation of light" in result
    assert "2A — People" in result
    assert "2B — Places" in result
    assert "2C — Objects and Elements" in result
    assert "2D — What Happens" in result
    assert "2E — Communicative Purpose" in result


@pytest.mark.asyncio
async def test_export_prose_contains_propositions(db_session) -> None:
    user = await make_user(db_session, email="analyst47@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id, data=SAMPLE_DATA)
    result = export_prose(mm)
    assert "Proposition 1" in result
    assert "What happens?" in result


@pytest.mark.asyncio
async def test_export_prose_empty_data(db_session) -> None:
    user = await make_user(db_session, email="analyst48@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id, data={})
    result = export_prose(mm)
    assert "# Prose Meaning Map" in result


# ---------------------------------------------------------------------------
# Feedback: resolve_feedback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_feedback_success(db_session) -> None:
    user = await make_user(db_session, email="analyst49@test.com")
    reviewer = await make_user(db_session, email="reviewer3@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id)
    fb = await make_meaning_map_feedback(db_session, mm.id, reviewer.id)
    assert fb.resolved is False
    resolved = await resolve_feedback(db_session, mm.id, fb.id)
    assert resolved.resolved is True


@pytest.mark.asyncio
async def test_resolve_feedback_raises_if_not_found(db_session) -> None:
    user = await make_user(db_session, email="analyst50@test.com")
    book = await make_bible_book(db_session)
    pericope = await make_pericope(db_session, book.id)
    mm = await make_meaning_map(db_session, pericope.id, user.id)
    with pytest.raises(NotFoundError, match=r"Feedback .* not found"):
        await resolve_feedback(db_session, mm.id, "nonexistent-id")


@pytest.mark.asyncio
async def test_resolve_feedback_wrong_meaning_map(db_session) -> None:
    user = await make_user(db_session, email="analyst51@test.com")
    reviewer = await make_user(db_session, email="reviewer4@test.com")
    book = await make_bible_book(db_session)
    p1 = await make_pericope(db_session, book.id, reference="Gen 1:1-5")
    p2 = await make_pericope(db_session, book.id, chapter_start=2, reference="Gen 2:1-5")
    mm1 = await make_meaning_map(db_session, p1.id, user.id)
    mm2 = await make_meaning_map(db_session, p2.id, user.id)
    fb = await make_meaning_map_feedback(db_session, mm1.id, reviewer.id)
    with pytest.raises(NotFoundError, match=r"Feedback .* not found"):
        await resolve_feedback(db_session, mm2.id, fb.id)


# ---------------------------------------------------------------------------
# Seed: seed_books
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_books_inserts_all_66(db_session) -> None:
    count = await seed_books(db_session)
    assert count == 66
    books = await list_books(db_session)
    assert len(books) == 66


@pytest.mark.asyncio
async def test_seed_books_idempotent(db_session) -> None:
    first = await seed_books(db_session)
    assert first == 66
    second = await seed_books(db_session)
    assert second == 0
    books = await list_books(db_session)
    assert len(books) == 66


@pytest.mark.asyncio
async def test_seed_books_ot_enabled_nt_disabled(db_session) -> None:
    await seed_books(db_session)
    books = await list_books(db_session)
    for book in books:
        if book.testament == "OT":
            assert book.is_enabled is True, f"{book.name} should be enabled"
        else:
            assert book.is_enabled is False, f"{book.name} should be disabled"


# ---------------------------------------------------------------------------
# Validation: ensure_ot
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_ot_passes_for_enabled_book(db_session) -> None:
    book = await make_bible_book(db_session, is_enabled=True)
    ensure_ot(book)  # should not raise


@pytest.mark.asyncio
async def test_ensure_ot_raises_for_disabled_book(db_session) -> None:
    book = await make_bible_book(
        db_session,
        name="Matthew",
        abbreviation="Matt",
        testament="NT",
        order=40,
        chapter_count=28,
        is_enabled=False,
    )
    with pytest.raises(AuthorizationError, match="not enabled for meaning map work"):
        ensure_ot(book)
