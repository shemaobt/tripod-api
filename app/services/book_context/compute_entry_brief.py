from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.book_context import BookContextDocument
from app.db.models.meaning_map import Pericope
from app.models.book_context import EstablishedItem, PassageEntryBriefResponse
from app.services.book_context.get_latest_approved import get_latest_approved


def _is_before(ref: dict[str, int], target_chapter: int, target_verse: int) -> bool:
    ch: int = ref.get("chapter", 0)
    v: int = ref.get("verse", 0)
    return ch < target_chapter or (ch == target_chapter and v < target_verse)


def _slice_participants(
    register: list[dict[str, Any]] | None,
    target_chapter: int,
    target_verse: int,
) -> list[dict[str, Any]]:
    result = []
    for p in register or []:
        entry = p.get("entry_verse", {})
        if not _is_before(entry, target_chapter, target_verse):
            continue
        sliced_arc = [
            a for a in p.get("arc", []) if _is_before(a.get("at", {}), target_chapter, target_verse)
        ]
        result.append({**p, "arc": sliced_arc})
    return result


def _slice_threads(
    threads: list[dict[str, Any]] | None,
    target_chapter: int,
    target_verse: int,
) -> list[dict[str, Any]]:
    result = []
    for t in threads or []:
        opened = t.get("opened_at", {})
        if not _is_before(opened, target_chapter, target_verse):
            continue
        sliced_status = [
            s
            for s in t.get("status_by_episode", [])
            if _is_before(s.get("at", {}), target_chapter, target_verse)
        ]
        resolved_at = t.get("resolved_at")
        is_resolved = resolved_at is not None and _is_before(
            resolved_at, target_chapter, target_verse
        )
        result.append(
            {
                **t,
                "status_by_episode": sliced_status,
                "is_resolved_at_entry": is_resolved,
            }
        )
    return result


def _filter_by_first_appears(
    items: list[dict[str, Any]] | None,
    key: str,
    target_chapter: int,
    target_verse: int,
) -> list[dict[str, Any]]:
    return [
        item
        for item in (items or [])
        if _is_before(item.get(key, {}), target_chapter, target_verse)
    ]


def _build_gloss_lookup(bcd: BookContextDocument) -> dict[str, str]:

    glosses: dict[str, str] = {}
    for section in [bcd.participant_register, bcd.places, bcd.objects, bcd.institutions]:
        for item in section or []:
            name = item.get("name", "")
            gloss = item.get("english_gloss", "")
            if name and gloss and name not in glosses:
                glosses[name] = gloss
    return glosses


def _enrich_glosses(items: list[dict[str, Any]], glosses: dict[str, str]) -> list[dict[str, Any]]:

    result = []
    for item in items:
        name = item.get("name", "")
        if name and not item.get("english_gloss") and name in glosses:
            item = {**item, "english_gloss": glosses[name]}
        result.append(item)
    return result


def _build_established_items(
    participants: list[dict[str, Any]],
    threads: list[dict[str, Any]],
    institutions: list[dict[str, Any]],
    places: list[dict[str, Any]] | None = None,
    objects: list[dict[str, Any]] | None = None,
) -> list[EstablishedItem]:
    items = []

    for p in participants:
        latest_state = ""
        if p.get("arc"):
            latest_state = p["arc"][-1].get("state", "")
        entry = p.get("entry_verse", {})
        ref = f"{entry.get('chapter', '')}:{entry.get('verse', '')}"
        items.append(
            EstablishedItem(
                category="participant",
                name=p.get("name", ""),
                english_gloss=p.get("english_gloss", ""),
                description=f"{p.get('name', '')}: {latest_state}",
                verse_reference=ref,
            )
        )

    for t in threads:
        if t.get("is_resolved_at_entry"):
            continue
        opened = t.get("opened_at", {})
        ref = f"{opened.get('chapter', '')}:{opened.get('verse', '')}"
        latest_status = ""
        if t.get("status_by_episode"):
            latest_status = t["status_by_episode"][-1].get("status", "")
        items.append(
            EstablishedItem(
                category="event",
                name=t.get("label", ""),
                description=latest_status,
                verse_reference=ref,
            )
        )

    for inst in institutions:
        invoked = inst.get("first_invoked", {})
        ref = f"{invoked.get('chapter', '')}:{invoked.get('verse', '')}"
        items.append(
            EstablishedItem(
                category="institution",
                name=inst.get("name", ""),
                description=inst.get("what_it_is", ""),
                verse_reference=ref,
            )
        )

    for pl in places or []:
        appears = pl.get("first_appears", {})
        ref = f"{appears.get('chapter', '')}:{appears.get('verse', '')}"
        items.append(
            EstablishedItem(
                category="place",
                name=pl.get("name", ""),
                english_gloss=pl.get("english_gloss", ""),
                description=pl.get("meaning_and_function", ""),
                verse_reference=ref,
            )
        )

    for obj in objects or []:
        appears = obj.get("first_appears", {})
        ref = f"{appears.get('chapter', '')}:{appears.get('verse', '')}"
        items.append(
            EstablishedItem(
                category="object",
                name=obj.get("name", ""),
                description=obj.get("what_it_is", ""),
                verse_reference=ref,
            )
        )

    return items


async def _is_first_pericope(
    db: AsyncSession,
    book_id: str,
    chapter_start: int,
    verse_start: int,
) -> bool:
    result = await db.execute(
        select(Pericope.id)
        .where(
            Pericope.book_id == book_id,
            or_(
                Pericope.chapter_start < chapter_start,
                and_(
                    Pericope.chapter_start == chapter_start,
                    Pericope.verse_start < verse_start,
                ),
            ),
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is None


async def compute_entry_brief(
    db: AsyncSession,
    pericope_id: str,
) -> PassageEntryBriefResponse:
    result = await db.execute(select(Pericope).where(Pericope.id == pericope_id))
    pericope = result.scalar_one_or_none()
    if not pericope:
        raise NotFoundError(f"Pericope {pericope_id} not found.")

    bcd = await get_latest_approved(db, pericope.book_id)
    if not bcd:
        raise NotFoundError(
            "No approved Book Context Document for this book. "
            "An admin or analyst must generate one and have it approved before mapping can begin."
        )

    is_first = await _is_first_pericope(
        db, pericope.book_id, pericope.chapter_start, pericope.verse_start
    )

    if is_first:
        return PassageEntryBriefResponse(
            participants=[],
            active_threads=[],
            places=[],
            objects=[],
            institutions=[],
            established_items=[
                EstablishedItem(
                    category="event",
                    name="Opening",
                    description="Nothing. This is the opening of the book.",
                    verse_reference="",
                )
            ],
            is_first_pericope=True,
            bcd_version=bcd.version,
        )

    target_ch = pericope.chapter_start
    target_v = pericope.verse_start

    gloss_lookup = _build_gloss_lookup(bcd)

    participants = _enrich_glosses(
        _slice_participants(bcd.participant_register, target_ch, target_v),
        gloss_lookup,
    )
    threads = _slice_threads(bcd.discourse_threads, target_ch, target_v)
    places = _enrich_glosses(
        _filter_by_first_appears(bcd.places, "first_appears", target_ch, target_v),
        gloss_lookup,
    )
    objects = _filter_by_first_appears(bcd.objects, "first_appears", target_ch, target_v)
    institutions = _filter_by_first_appears(bcd.institutions, "first_invoked", target_ch, target_v)

    established_items = _build_established_items(
        participants,
        threads,
        institutions,
        places=places,
        objects=objects,
    )

    return PassageEntryBriefResponse.model_validate(
        {
            "participants": participants,
            "active_threads": threads,
            "places": places,
            "objects": objects,
            "institutions": institutions,
            "established_items": established_items,
            "is_first_pericope": False,
            "bcd_version": bcd.version,
        }
    )
