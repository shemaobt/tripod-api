import base64

from fastapi import APIRouter, File, Form, Response, UploadFile
from pydantic import BaseModel, Field

from app.api.project_health._deps import interview_token_dep
from app.core.exceptions import ValidationError
from app.db.models.project_health import PHLanguage
from app.services.project_health.voice import synthesize_speech, transcribe_audio

router = APIRouter()

MAX_AUDIO_BYTES = 25 * 1024 * 1024
MAX_TTS_CHARS = 3000


class VoiceTranscribeResponse(BaseModel):
    transcript: str


class VoiceSpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TTS_CHARS)
    language: PHLanguage


class VoiceSpeakResponse(BaseModel):
    audio_base64: str
    mime_type: str
    etag: str
    cached: bool


@router.post(
    "/interviews/{interview_id}/voice/transcribe",
    response_model=VoiceTranscribeResponse,
    dependencies=[interview_token_dep],
)
async def transcribe_endpoint(
    interview_id: str,
    file: UploadFile = File(...),
    mime_type: str | None = Form(default=None),
    language: PHLanguage | None = Form(default=None),
) -> VoiceTranscribeResponse:
    audio_bytes = await file.read()
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise ValidationError("Audio payload exceeds 25 MB limit")
    transcript = await transcribe_audio(
        audio_bytes,
        language=language.value if language else None,
        filename=file.filename,
        mime_type=mime_type or file.content_type,
    )
    return VoiceTranscribeResponse(transcript=transcript)


@router.post(
    "/interviews/{interview_id}/voice/speak",
    response_model=VoiceSpeakResponse,
    dependencies=[interview_token_dep],
)
async def speak_endpoint(
    interview_id: str,
    payload: VoiceSpeakRequest,
    response: Response,
) -> VoiceSpeakResponse:
    entry, cached = await synthesize_speech(payload.text, language=payload.language.value)
    response.headers["ETag"] = entry.etag
    return VoiceSpeakResponse(
        audio_base64=base64.b64encode(entry.audio).decode("ascii"),
        mime_type=entry.mime_type,
        etag=entry.etag,
        cached=cached,
    )
