import logging
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.core.exceptions import ValidationError
from app.services.translation_helper.audio_cache import AudioCache, audio_cache
from app.services.translation_helper.synthesize_speech import synthesize_speech
from app.services.translation_helper.transcribe_audio import transcribe_audio

_TRANSCRIBE_MOD = sys.modules["app.services.translation_helper.transcribe_audio"]


def _settings() -> Settings:
    return Settings(database_url="sqlite+aiosqlite:///./test.db", google_api_key="fake")


def _patch_genai_client(monkeypatch, return_text: str) -> AsyncMock:
    aio_models = SimpleNamespace(
        generate_content=AsyncMock(return_value=SimpleNamespace(text=return_text))
    )
    aio = SimpleNamespace(models=aio_models)
    fake_client = SimpleNamespace(aio=aio)

    def fake_constructor(*, api_key):
        return fake_client

    monkeypatch.setattr(_TRANSCRIBE_MOD.genai, "Client", fake_constructor)
    return aio_models.generate_content


@pytest.mark.asyncio
async def test_transcribe_audio_returns_trimmed_text(monkeypatch) -> None:
    mock_call = _patch_genai_client(monkeypatch, "  hello world  ")
    text = await transcribe_audio(b"abc", filename="clip.wav", settings=_settings())
    assert text == "hello world"
    assert mock_call.await_count == 1


@pytest.mark.asyncio
async def test_transcribe_audio_sniffs_wav_when_filename_and_mime_missing(
    monkeypatch,
) -> None:
    """B-4: unknown audio + no metadata should sniff the magic bytes, not fall back
    silently to audio/mpeg."""
    mock_call = _patch_genai_client(monkeypatch, "hello")
    wav_header = b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 16
    await transcribe_audio(wav_header, settings=_settings())
    sent_mime = mock_call.await_args.kwargs["contents"][0].inline_data.mime_type
    assert sent_mime == "audio/wav"


@pytest.mark.asyncio
async def test_transcribe_audio_warns_on_missing_mime(monkeypatch, caplog) -> None:
    """B-4: when neither filename, mime, nor a sniffable magic byte is available,
    we should log a warning so the operator can debug a confused Gemini call."""
    _patch_genai_client(monkeypatch, "ok")
    caplog.set_level(logging.WARNING, logger="app.services.translation_helper.transcribe_audio")
    await transcribe_audio(
        b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b", settings=_settings()
    )
    assert any("mime-type fallback" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_transcribe_audio_rejects_empty_payload(monkeypatch) -> None:
    _patch_genai_client(monkeypatch, "ignored")
    with pytest.raises(ValidationError):
        await transcribe_audio(b"", filename="clip.wav", settings=_settings())


@pytest.mark.asyncio
async def test_transcribe_audio_raises_when_empty_response(monkeypatch) -> None:
    _patch_genai_client(monkeypatch, "")
    with pytest.raises(ValidationError):
        await transcribe_audio(b"abc", filename="x.wav", settings=_settings())


def _audio_response(audio: bytes) -> SimpleNamespace:
    return SimpleNamespace(audio_content=audio)


@pytest.mark.asyncio
async def test_synthesize_speech_caches_on_repeat_calls() -> None:
    audio_cache.clear()
    fake_client = SimpleNamespace(
        synthesize_speech=AsyncMock(return_value=_audio_response(b"MP3DATA"))
    )

    entry1, cached1 = await synthesize_speech("hello", language_code="en-US", client=fake_client)
    entry2, cached2 = await synthesize_speech("hello", language_code="en-US", client=fake_client)

    assert cached1 is False
    assert cached2 is True
    assert entry1.audio == b"MP3DATA"
    assert entry2.etag == entry1.etag
    assert fake_client.synthesize_speech.await_count == 1


def _voice_name_of(call) -> str:
    """Pull the VoiceSelectionParams.name out of a mocked synthesize_speech call."""
    request = call.kwargs.get("request")
    return request.voice.name


@pytest.mark.asyncio
async def test_synthesize_speech_detects_portuguese_and_picks_chirp3_hd() -> None:
    audio_cache.clear()
    fake_client = SimpleNamespace(
        synthesize_speech=AsyncMock(return_value=_audio_response(b"PT_MP3"))
    )
    await synthesize_speech(
        "Olá, conte-me uma história sobre o Filho Pródigo, por favor.",
        client=fake_client,
    )
    assert _voice_name_of(fake_client.synthesize_speech.await_args) == "pt-BR-Chirp3-HD-Achird"


@pytest.mark.asyncio
async def test_synthesize_speech_detects_spanish_and_picks_studio() -> None:
    audio_cache.clear()
    fake_client = SimpleNamespace(
        synthesize_speech=AsyncMock(return_value=_audio_response(b"ES_MP3"))
    )
    await synthesize_speech(
        "Hola, cuéntame una historia sobre la oveja perdida, por favor.",
        client=fake_client,
    )
    assert _voice_name_of(fake_client.synthesize_speech.await_args) == "es-ES-Studio-C"


@pytest.mark.asyncio
async def test_synthesize_speech_falls_back_to_default_on_short_text() -> None:
    audio_cache.clear()
    fake_client = SimpleNamespace(
        synthesize_speech=AsyncMock(return_value=_audio_response(b"OK_MP3"))
    )
    await synthesize_speech("ok then", client=fake_client)
    assert _voice_name_of(fake_client.synthesize_speech.await_args) == "en-US-Studio-O"


@pytest.mark.asyncio
async def test_synthesize_speech_explicit_language_overrides_detection() -> None:
    audio_cache.clear()
    fake_client = SimpleNamespace(
        synthesize_speech=AsyncMock(return_value=_audio_response(b"FORCED_MP3"))
    )
    await synthesize_speech(
        "Olá, conte-me uma história sobre o Filho Pródigo.",
        language_code="en-US",
        client=fake_client,
    )
    assert _voice_name_of(fake_client.synthesize_speech.await_args) == "en-US-Studio-O"


@pytest.mark.asyncio
async def test_synthesize_speech_rejects_empty_text() -> None:
    fake_client = SimpleNamespace(synthesize_speech=AsyncMock())
    with pytest.raises(ValidationError):
        await synthesize_speech("   ", client=fake_client)


@pytest.mark.asyncio
async def test_synthesize_speech_raises_when_no_audio() -> None:
    audio_cache.clear()
    fake_client = SimpleNamespace(synthesize_speech=AsyncMock(return_value=_audio_response(b"")))
    with pytest.raises(ValidationError):
        await synthesize_speech("hello world", client=fake_client)


def test_audio_cache_lru_eviction() -> None:
    cache = AudioCache(max_entries=2, ttl_seconds=999)
    cache.put("a", b"1", "audio/mpeg")
    cache.put("b", b"2", "audio/mpeg")
    cache.put("c", b"3", "audio/mpeg")
    assert cache.get("a") is None
    assert cache.get("b") is not None
    assert cache.get("c") is not None
