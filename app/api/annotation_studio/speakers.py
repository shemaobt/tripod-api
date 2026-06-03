from fastapi import APIRouter, status

from app.api.annotation_studio._deps import CurrentUser, Db
from app.models.annotation_studio import SpeakerCreate, SpeakerResponse, SpeakerUpdate
from app.services.annotation_studio import speaker_service

router = APIRouter()


@router.get("/languages/{language_id}/speakers", response_model=list[SpeakerResponse])
async def list_speakers(language_id: str, db: Db, _: CurrentUser) -> list[SpeakerResponse]:
    speakers = await speaker_service.list_speakers(db, language_id)
    return [SpeakerResponse.model_validate(s) for s in speakers]


@router.post(
    "/languages/{language_id}/speakers",
    response_model=SpeakerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_speaker(
    language_id: str, payload: SpeakerCreate, db: Db, _: CurrentUser
) -> SpeakerResponse:
    speaker = await speaker_service.create_speaker(
        db, language_id, payload.label, payload.display_name
    )
    return SpeakerResponse.model_validate(speaker)


@router.patch("/speakers/{speaker_id}", response_model=SpeakerResponse)
async def update_speaker(
    speaker_id: str, payload: SpeakerUpdate, db: Db, _: CurrentUser
) -> SpeakerResponse:
    speaker = await speaker_service.update_speaker(db, speaker_id, payload.display_name)
    return SpeakerResponse.model_validate(speaker)


@router.delete("/speakers/{speaker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_speaker(speaker_id: str, db: Db, _: CurrentUser) -> None:
    await speaker_service.delete_speaker(db, speaker_id)
