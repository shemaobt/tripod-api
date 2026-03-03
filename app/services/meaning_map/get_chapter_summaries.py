from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import MeaningMap, Pericope
from app.models.meaning_map import ChapterSummary


async def get_chapter_summaries(db: AsyncSession, book_id: str) -> list[ChapterSummary]:
    # Fetch all pericopes and their meaning maps for the given book
    stmt = (
        select(Pericope, MeaningMap.status)
        .outerjoin(MeaningMap, MeaningMap.pericope_id == Pericope.id)
        .where(Pericope.book_id == book_id)
    )
    result = await db.execute(stmt)
    rows = result.all()

    # We need to determine the max chapter to return a continuous list 1..N
    # Alternatively, the chapters can be sparse, but usually we want to return the chapters that exist
    # Actually, BookPage frontend handles sparse returns by padding up to book.chapter_count.
    # We will build a dictionary of tallies per chapter.
    tallies: dict[int, dict[str, int]] = {}

    for row in rows:
        pericope = row[0]
        status = row[1]
        
        # A pericope spans from chapter_start to chapter_end (inclusive)
        for ch in range(pericope.chapter_start, pericope.chapter_end + 1):
            if ch not in tallies:
                tallies[ch] = {"pericope": 0, "draft": 0, "cross_check": 0, "approved": 0}
            
            tallies[ch]["pericope"] += 1
            if status == "draft":
                tallies[ch]["draft"] += 1
            elif status == "cross_check":
                tallies[ch]["cross_check"] += 1
            elif status == "approved":
                tallies[ch]["approved"] += 1

    # Convert the tallies dictionary to a sorted list of ChapterSummary objects
    summaries = []
    for ch in sorted(tallies.keys()):
        t = tallies[ch]
        summaries.append(
            ChapterSummary(
                chapter=ch,
                pericope_count=t["pericope"],
                draft_count=t["draft"],
                cross_check_count=t["cross_check"],
                approved_count=t["approved"],
            )
        )

    return summaries
