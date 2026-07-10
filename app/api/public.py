from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.public_request import (
    PublicLanguageOption,
    PublicLanguageRequestCreate,
    PublicProjectRequestCreate,
    PublicRequestResponse,
)
from app.services import language_service, public_request_service

router = APIRouter()


@router.get("/languages", response_model=list[PublicLanguageOption])
async def list_public_languages(
    db: AsyncSession = Depends(get_db),
) -> list[PublicLanguageOption]:
    languages = await language_service.list_languages(db)
    return [PublicLanguageOption.model_validate(lang) for lang in languages]


@router.post(
    "/requests/language",
    response_model=PublicRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_language_creation(
    payload: PublicLanguageRequestCreate,
    db: AsyncSession = Depends(get_db),
) -> PublicRequestResponse:
    await public_request_service.verify_recaptcha(payload.recaptcha_token)
    request = await public_request_service.create_language_request(
        db,
        requester_name=payload.requester_name,
        requester_email=payload.requester_email,
        name=payload.name,
        code=payload.code,
    )
    return PublicRequestResponse.model_validate(request)


@router.post(
    "/requests/project",
    response_model=PublicRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_project_creation(
    payload: PublicProjectRequestCreate,
    db: AsyncSession = Depends(get_db),
) -> PublicRequestResponse:
    await public_request_service.verify_recaptcha(payload.recaptcha_token)
    request = await public_request_service.create_project_request(
        db,
        requester_name=payload.requester_name,
        requester_email=payload.requester_email,
        name=payload.name,
        language_id=payload.language_id,
        description=payload.description,
    )
    return PublicRequestResponse.model_validate(request)
