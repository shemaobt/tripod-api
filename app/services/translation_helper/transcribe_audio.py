from __future__ import annotations

import logging

from google import genai
from google.genai import types

from app.core.config import Settings, get_settings
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

TRANSCRIPTION_MODEL = "gemini-3-flash-preview"
TRANSCRIBE_INSTRUCTION = (
    "Transcribe this audio file. Provide only the transcribed text without any"
    " additional commentary."
)


def _guess_mime_type(filename: str | None, fallback: str | None) -> str:
    if filename:
        lower = filename.lower()
        if lower.endswith(".mp3"):
            return "audio/mp3"
        if lower.endswith(".wav"):
            return "audio/wav"
        if lower.endswith(".m4a"):
            return "audio/mp4"
        if lower.endswith(".webm"):
            return "audio/webm"
        if lower.endswith(".ogg"):
            return "audio/ogg"
    if fallback:
        return fallback
    return "audio/mpeg"


async def transcribe_audio(
    audio_bytes: bytes,
    *,
    filename: str | None = None,
    mime_type: str | None = None,
    settings: Settings | None = None,
) -> str:
    if not audio_bytes:
        raise ValidationError("Audio payload is empty")
    settings = settings or get_settings()
    resolved_mime = _guess_mime_type(filename, mime_type)

    client = genai.Client(api_key=settings.google_api_key)
    response = await client.aio.models.generate_content(
        model=TRANSCRIPTION_MODEL,
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type=resolved_mime),
            TRANSCRIBE_INSTRUCTION,
        ],
    )
    text = (response.text or "").strip()
    if not text:
        raise ValidationError("Transcription returned empty text")
    return text
