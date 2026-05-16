import base64

from fastapi import APIRouter, File, Form, Response, UploadFile

from app.api.translation_helper._deps import th_access
from app.core.exceptions import ValidationError
from app.models.translation_helper import SpeakRequest, SpeakResponse, TranscribeResponse
from app.services import translation_helper_service as th_service

router = APIRouter()

MAX_AUDIO_BYTES = 25 * 1024 * 1024


@router.post(
    "/audio/transcribe",
    response_model=TranscribeResponse,
    dependencies=[th_access],
)
async def transcribe(
    file: UploadFile = File(...),
    mime_type: str | None = Form(default=None),
) -> TranscribeResponse:
    audio_bytes = await file.read()
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise ValidationError("Audio payload exceeds 25 MB limit")
    text = await th_service.transcribe_audio(
        audio_bytes,
        filename=file.filename,
        mime_type=mime_type or file.content_type,
    )
    return TranscribeResponse(text=text)


@router.post(
    "/audio/speak",
    response_model=SpeakResponse,
    dependencies=[th_access],
)
async def speak(payload: SpeakRequest, response: Response) -> SpeakResponse:
    entry, cached = await th_service.synthesize_speech(
        payload.text,
        language_code=payload.language_code,
        voice_name=payload.voice_name,
    )
    response.headers["ETag"] = entry.etag
    return SpeakResponse(
        audio_base64=base64.b64encode(entry.audio).decode("ascii"),
        mime_type=entry.mime_type,
        etag=entry.etag,
        cached=cached,
    )
