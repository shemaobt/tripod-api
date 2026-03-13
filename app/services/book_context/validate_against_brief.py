import re

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import MeaningMap, Pericope
from app.models.book_context import ValidationIssue


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


async def validate_map_against_brief(
    db: AsyncSession,
    meaning_map: MeaningMap,
) -> list[ValidationIssue]:
    result = await db.execute(select(Pericope).where(Pericope.id == meaning_map.pericope_id))
    pericope = result.scalar_one_or_none()
    if not pericope:
        return []

    data = meaning_map.data or {}
    issues: list[ValidationIssue] = []

    is_first = await _is_first_pericope(
        db, pericope.book_id, pericope.chapter_start, pericope.verse_start
    )

    established = data.get("already_established", [])

    if not is_first and not established:
        issues.append(
            ValidationIssue(
                severity="error",
                message="Already Established list is empty for a non-first pericope.",
                section="already_established",
            )
        )

    established_names = {
        item.get("name", "").strip().lower()
        for item in established
        if item.get("name", "").strip().lower()
        and item.get("name", "").strip().lower() not in ("opening", "nothing")
    }

    if not established_names:
        return issues

    propositions = data.get("level_3_propositions", [])
    for prop in propositions:
        prop_num = prop.get("proposition_number", "?")
        for content_item in prop.get("content", []):
            answer = content_item.get("answer", "")
            for name in established_names:
                if re.search(rf"\b{re.escape(name)}\b", answer, re.IGNORECASE):
                    issues.append(
                        ValidationIssue(
                            severity="warning",
                            message=(
                                f"Established name '{name.title()}' found in "
                                f"proposition {prop_num}. "
                                "Consider using a generic reference instead."
                            ),
                            section=f"prop_{prop_num}",
                        )
                    )

    return issues
