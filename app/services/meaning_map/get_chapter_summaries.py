from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import MeaningMap, Pericope
from app.models.meaning_map import ChapterSummary


async def get_chapter_summaries(db: AsyncSession, book_id: str) -> list[ChapterSummary]:
    """Return per-chapter pericope/status tallies, selecting only needed columns."""
    stmt = (
        select(Pericope.chapter_start, Pericope.chapter_end, MeaningMap.status)
        .outerjoin(MeaningMap, MeaningMap.pericope_id == Pericope.id)
        .where(Pericope.book_id == book_id)
    )
    result = await db.execute(stmt)
    rows = result.all()

    tallies: dict[int, dict[str, int]] = {}

    for chapter_start, chapter_end, status in rows:
        for ch in range(chapter_start, chapter_end + 1):
            if ch not in tallies:
                tallies[ch] = {"pericope": 0, "draft": 0, "cross_check": 0, "approved": 0}

            tallies[ch]["pericope"] += 1
            if status == "draft":
                tallies[ch]["draft"] += 1
            elif status == "cross_check":
                tallies[ch]["cross_check"] += 1
            elif status == "approved":
                tallies[ch]["approved"] += 1

    return [
        ChapterSummary(
            chapter=ch,
            pericope_count=t["pericope"],
            draft_count=t["draft"],
            cross_check_count=t["cross_check"],
            approved_count=t["approved"],
        )
        for ch, t in sorted(tallies.items())
    ]
