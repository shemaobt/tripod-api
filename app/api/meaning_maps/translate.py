from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.meaning_maps._deps import mm_access
from app.core.database import get_db
from app.services.meaning_map.translate import translate_meaning_map

router = APIRouter()


class TranslateRequest(BaseModel):
    language: str = Field(min_length=2, max_length=10)


class TranslateResponse(BaseModel):
    language: str
    data: dict


@router.post("/{map_id}/translate", response_model=TranslateResponse, dependencies=[mm_access])
async def translate_map(
    map_id: str,
    payload: TranslateRequest,
    db: AsyncSession = Depends(get_db),
) -> TranslateResponse:
    translated = await translate_meaning_map(db, map_id, payload.language)
    return TranslateResponse(language=payload.language, data=translated)
