"""Síntese de fala da plataforma (ElevenLabs), compartilhada entre os apps.

Texto + idioma → MP3. O cache é **durável, no bucket genérico**, com chave endereçada por
conteúdo — então cada frase é sintetizada **uma vez, para sempre, para todos os apps**, e
um worker frio não re-cobra a ElevenLabs. É a diferença para os dois clientes que já
existem no repo (`project_health/voice/` e `translation_helper/synthesize_speech.py`), que
carregam a MESMA classe `AudioCache` copiada e colada: um LRU em processo, de 100 entradas
e TTL de 24 h, que evapora a cada deploy.

> Aqueles dois **ainda não** usam este serviço — migrá-los é follow-up (o módulo de voz do
> project_health não tem nenhum teste hoje e é produto vivo). Até lá o repo tem três
> caminhos para a ElevenLabs, e isso é dívida conhecida, não descuido.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import ValidationError
from app.services.platform.voices import language_hint, resolve_voice

logger = logging.getLogger(__name__)

MIME_TYPE = "audio/mpeg"

_DEFAULT_CLIENT: httpx.AsyncClient | None = None


@dataclass(frozen=True)
class SynthesizedSpeech:
    audio: bytes
    mime_type: str
    etag: str
    #: Veio do bucket (a ElevenLabs não foi chamada).
    cached: bool


class SpeechStore(Protocol):
    """O seam do bucket: os testes passam um dicionário em memória, sem GCS."""

    async def get(self, key: str) -> bytes | None: ...

    async def put(self, key: str, data: bytes, content_type: str) -> None: ...


def cache_key(text: str, *, voice_id: str, model: str) -> str:
    """Chave endereçada por conteúdo: mesmo texto + mesma voz + mesmo modelo = mesmo objeto."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"tts/{voice_id}/{model}/{digest}.mp3"


async def synthesize_speech(
    text: str,
    *,
    language: str,
    settings: Settings | None = None,
    client: httpx.AsyncClient | None = None,
    store: SpeechStore | None = None,
) -> SynthesizedSpeech:
    """Fala `text` em `language` (locale BCP-47, ex.: `pt-BR`), servindo do cache quando possível.

    `settings`, `client` e `store` são injetáveis — é o que torna o serviço testável sem
    rede e sem GCS.
    """
    if not text or not text.strip():
        raise ValidationError("text must not be empty")

    cfg = settings or get_settings()
    if not cfg.elevenlabs_api_key:
        # ponytail: o project_health usa uma SEGUNDA chave (`ph_elevenlabs_api_key`). Quando
        # ele migrar para cá, as duas viram uma.
        raise ValidationError("ELEVENLABS_API_KEY is not configured")

    voice_id = resolve_voice(language)
    key = cache_key(text, voice_id=voice_id, model=cfg.elevenlabs_tts_model)
    speech_store = store or _default_store(cfg)

    cached = await speech_store.get(key)
    if cached is not None:
        return SynthesizedSpeech(cached, MIME_TYPE, _etag(cached), cached=True)

    audio = await _synthesize(text, voice_id=voice_id, language=language, cfg=cfg, client=client)
    await speech_store.put(key, audio, MIME_TYPE)
    return SynthesizedSpeech(audio, MIME_TYPE, _etag(audio), cached=False)


async def _synthesize(
    text: str,
    *,
    voice_id: str,
    language: str,
    cfg: Settings,
    client: httpx.AsyncClient | None,
) -> bytes:
    body: dict[str, object] = {
        "text": text,
        "model_id": cfg.elevenlabs_tts_model,
        "output_format": cfg.elevenlabs_output_format,
        "language_code": language_hint(language),
        # ponytail: sem `voice_settings` — os defaults da voz servem para uma pergunta curta
        # e neutra. O botão de calibragem, se um dia a fala soar corrida numa entrevista, é
        # `"voice_settings": {"speed": 0.9}` (faixa util 0.7-1.2, default 1.0).
    }

    http = client or _make_client()
    response = await http.post(
        f"{cfg.elevenlabs_base_url}/v1/text-to-speech/{voice_id}",
        json=body,
        headers={"xi-api-key": cfg.elevenlabs_api_key, "accept": MIME_TYPE},
    )
    if response.status_code >= 400:
        logger.warning(
            "ElevenLabs TTS failed: status=%s body=%s",
            response.status_code,
            response.text[:500],
        )
        raise ValidationError(f"TTS request failed with status {response.status_code}")

    return bytes(response.content)


def _etag(audio: bytes) -> str:
    return hashlib.sha256(audio).hexdigest()[:32]


def _default_store(cfg: Settings) -> SpeechStore:
    from app.services.platform.storage import GcsPlatformStore

    return GcsPlatformStore(cfg)


def _make_client() -> httpx.AsyncClient:
    global _DEFAULT_CLIENT
    if _DEFAULT_CLIENT is None:
        _DEFAULT_CLIENT = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))
    return _DEFAULT_CLIENT
