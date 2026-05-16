from __future__ import annotations

import asyncio
import logging

from google.cloud import texttospeech

from app.core.exceptions import ValidationError
from app.services.translation_helper.audio_cache import CachedAudio, audio_cache

logger = logging.getLogger(__name__)

VOICE_MAP: dict[str, dict[str, str]] = {
    "en-US": {"language_code": "en-US", "name": "en-US-Neural2-C", "gender": "FEMALE"},
    "en-GB": {"language_code": "en-GB", "name": "en-GB-Neural2-C", "gender": "FEMALE"},
    "es-ES": {"language_code": "es-ES", "name": "es-ES-Neural2-C", "gender": "FEMALE"},
    "es-MX": {"language_code": "es-US", "name": "es-US-Neural2-A", "gender": "FEMALE"},
    "fr-FR": {"language_code": "fr-FR", "name": "fr-FR-Neural2-C", "gender": "FEMALE"},
    "de-DE": {"language_code": "de-DE", "name": "de-DE-Neural2-C", "gender": "FEMALE"},
    "it-IT": {"language_code": "it-IT", "name": "it-IT-Neural2-A", "gender": "FEMALE"},
    "pt-BR": {"language_code": "pt-BR", "name": "pt-BR-Neural2-C", "gender": "FEMALE"},
    "ja-JP": {"language_code": "ja-JP", "name": "ja-JP-Neural2-B", "gender": "FEMALE"},
    "ko-KR": {"language_code": "ko-KR", "name": "ko-KR-Neural2-B", "gender": "FEMALE"},
    "zh-CN": {"language_code": "cmn-CN", "name": "cmn-CN-Wavenet-A", "gender": "FEMALE"},
    "hi-IN": {"language_code": "hi-IN", "name": "hi-IN-Neural2-A", "gender": "FEMALE"},
    "ar-SA": {"language_code": "ar-XA", "name": "ar-XA-Wavenet-A", "gender": "FEMALE"},
    "ru-RU": {"language_code": "ru-RU", "name": "ru-RU-Wavenet-C", "gender": "FEMALE"},
    "nl-NL": {"language_code": "nl-NL", "name": "nl-NL-Wavenet-A", "gender": "FEMALE"},
    "sv-SE": {"language_code": "sv-SE", "name": "sv-SE-Wavenet-A", "gender": "FEMALE"},
    "da-DK": {"language_code": "da-DK", "name": "da-DK-Wavenet-A", "gender": "FEMALE"},
}


def _make_client() -> texttospeech.TextToSpeechAsyncClient:
    return texttospeech.TextToSpeechAsyncClient()


def _resolve_voice(language_code: str, voice_name: str | None) -> dict[str, str]:
    config = VOICE_MAP.get(language_code) or VOICE_MAP["en-US"]
    if voice_name:
        return {
            "language_code": config["language_code"],
            "name": voice_name,
            "gender": config["gender"],
        }
    return config


async def synthesize_speech(
    text: str,
    *,
    language_code: str = "en-US",
    voice_name: str | None = None,
    client: texttospeech.TextToSpeechAsyncClient | None = None,
) -> tuple[CachedAudio, bool]:
    """Return (cached audio entry, cached?) tuple."""
    if not text or not text.strip():
        raise ValidationError("text must not be empty")

    cache_key = audio_cache.make_key(text, language_code, voice_name)
    cached = audio_cache.get(cache_key)
    if cached is not None:
        return cached, True

    voice_cfg = _resolve_voice(language_code, voice_name)
    gender_enum = getattr(
        texttospeech.SsmlVoiceGender, voice_cfg["gender"], texttospeech.SsmlVoiceGender.NEUTRAL
    )

    tts_client = client or _make_client()
    request = texttospeech.SynthesizeSpeechRequest(
        input=texttospeech.SynthesisInput(text=text),
        voice=texttospeech.VoiceSelectionParams(
            language_code=voice_cfg["language_code"],
            name=voice_cfg["name"],
            ssml_gender=gender_enum,
        ),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0,
        ),
    )
    response = await tts_client.synthesize_speech(request=request)
    audio_bytes = bytes(response.audio_content) if response.audio_content else b""
    if not audio_bytes:
        raise ValidationError("TTS returned empty audio content")
    entry = audio_cache.put(cache_key, audio_bytes, mime_type="audio/mpeg")
    await asyncio.sleep(0)
    return entry, False
