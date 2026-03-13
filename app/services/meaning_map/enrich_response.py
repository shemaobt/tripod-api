from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import MeaningMap
from app.models.meaning_map import MeaningMapResponse
from app.services.meaning_map.get_pericope_with_book import get_pericope_with_book


async def enrich_meaning_map(db: AsyncSession, mm: MeaningMap) -> MeaningMapResponse:
    """Build a MeaningMapResponse with book/pericope details attached."""
    pericope, book = await get_pericope_with_book(db, mm.pericope_id)
    resp = MeaningMapResponse.model_validate(mm)
    resp.book_id = book.id
    resp.book_name = book.name
    resp.pericope_reference = pericope.reference
    return resp
