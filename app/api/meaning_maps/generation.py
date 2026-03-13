import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.meaning_maps._deps import mm_analyst
from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.core.qdrant import get_qdrant_client
from app.db.models.auth import User
from app.db.models.meaning_map import MeaningMap as MeaningMapModel
from app.models.meaning_map import MeaningMapGenerateRequest, MeaningMapResponse
from app.services import meaning_map_service
from app.services.book_context.compute_entry_brief import compute_entry_brief
from app.services.meaning_map.generator import GenerationError
from app.services.meaning_map.generator import generate_meaning_map as run_generation

logger = logging.getLogger(__name__)

router = APIRouter()


async def _enrich(db: AsyncSession, mm: MeaningMapModel) -> MeaningMapResponse:
    return await meaning_map_service.enrich_meaning_map(db, mm)


@router.post(
    "/generate",
    response_model=MeaningMapResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[mm_analyst],
)
async def generate_meaning_map(
    payload: MeaningMapGenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeaningMapResponse:
    pericope, book = await meaning_map_service.get_pericope_with_book(db, payload.pericope_id)
    meaning_map_service.ensure_ot(book)

    bcd_version: int | None = None
    entry_brief_data: dict | None = None
    try:
        entry_brief = await compute_entry_brief(db, payload.pericope_id)
        bcd_version = entry_brief.bcd_version
        entry_brief_data = entry_brief.model_dump()
    except Exception:
        logger.warning(
            "Entry brief computation failed for pericope %s — generating without Book Context",
            payload.pericope_id,
            exc_info=True,
        )

    try:
        qdrant = get_qdrant_client()
    except RuntimeError as exc:
        raise GenerationError("RAG service is not available. Contact an administrator.") from exc
    try:
        generated_data = await run_generation(
            pericope.reference,
            qdrant_client=qdrant,
            entry_brief=entry_brief_data,
        )
    except GenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    mm = await meaning_map_service.create_meaning_map(
        db,
        pericope_id=payload.pericope_id,
        analyst_id=user.id,
        data=generated_data,
        bcd_version_at_creation=bcd_version,
    )
    return await _enrich(db, mm)
