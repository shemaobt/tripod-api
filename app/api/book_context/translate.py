from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.book_context._deps import mm_access
from app.core.database import get_db
from app.services.book_context.translate import translate_bcd

router = APIRouter()


class TranslateRequest(BaseModel):
    language: str = Field(min_length=2, max_length=10)


class TranslateResponse(BaseModel):
    language: str
    data: dict


@router.post("/{bcd_id}/translate", response_model=TranslateResponse, dependencies=[mm_access])
async def translate_bcd_endpoint(
    bcd_id: str,
    payload: TranslateRequest,
    db: AsyncSession = Depends(get_db),
) -> TranslateResponse:
    translated = await translate_bcd(db, bcd_id, payload.language)
    return TranslateResponse(language=payload.language, data=translated)
