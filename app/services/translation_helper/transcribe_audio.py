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


def _sniff_mime_from_bytes(audio_bytes: bytes) -> str | None:
    """Best-effort MIME detection from the first few bytes of common audio formats."""
    if len(audio_bytes) < 12:
        return None
    head = audio_bytes[:12]
    # RIFF....WAVE
    if head[0:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "audio/wav"
    # OggS (Ogg/Opus container)
    if head[0:4] == b"OggS":
        return "audio/ogg"
    # ID3-tagged MP3
    if head[0:3] == b"ID3":
        return "audio/mp3"
    # MPEG frame sync (raw MP3, no ID3 header)
    if head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
        return "audio/mp3"
    # EBML — WebM/Matroska
    if head[0:4] == b"\x1a\x45\xdf\xa3":
        return "audio/webm"
    return None


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
    if resolved_mime == "audio/mpeg" and not filename and not mime_type:
        sniffed = _sniff_mime_from_bytes(audio_bytes)
        if sniffed is not None:
            resolved_mime = sniffed
        else:
            logger.warning(
                "Audio mime-type fallback hit for transcription: filename=%r mime=%r",
                filename,
                mime_type,
            )

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
