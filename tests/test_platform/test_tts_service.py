from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.core.exceptions import ValidationError
from app.services.platform.tts import cache_key, synthesize_speech
from app.services.platform.voices import VOICES, resolve_voice

MP3 = b"\xff\xfb\x90fake-mpeg-frame"
QUESTION = "Onde essa história acontece?"


def _settings(**over: Any) -> Settings:
    fields: dict[str, Any] = {
        "database_url": "sqlite+aiosqlite:///./test.db",
        "google_api_key": "fake-google",
        "elevenlabs_api_key": "fake-elevenlabs",
        "gcs_platform_bucket": "tripod-platform-test",
    }
    fields.update(over)
    return Settings(**fields)


def _ok(audio: bytes = MP3) -> SimpleNamespace:
    return SimpleNamespace(status_code=200, content=audio, text="")


def _err(status: int) -> SimpleNamespace:
    return SimpleNamespace(status_code=status, content=b"", text="boom")


def _client(*responses: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(post=AsyncMock(side_effect=list(responses) or [_ok()]))


class MemoryStore:
    """Bucket em memória — o seam que substitui o GCS nos testes."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.reads = 0
        self.writes = 0

    async def get(self, key: str) -> bytes | None:
        self.reads += 1
        return self.objects.get(key)

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        self.writes += 1
        self.objects[key] = data


async def test_sintetiza_e_devolve_o_mp3() -> None:
    client = _client(_ok())
    store = MemoryStore()

    result = await synthesize_speech(
        QUESTION, language="pt-BR", settings=_settings(), client=client, store=store
    )

    assert result.audio == MP3
    assert result.mime_type == "audio/mpeg"
    assert result.cached is False
    assert client.post.await_count == 1

    url, kwargs = client.post.await_args
    assert VOICES["pt-BR"] in url[0]
    assert kwargs["json"]["text"] == QUESTION
    assert kwargs["json"]["model_id"] == "eleven_multilingual_v2"
    assert kwargs["headers"]["xi-api-key"] == "fake-elevenlabs"


async def test_a_segunda_chamada_do_mesmo_texto_nao_toca_a_elevenlabs() -> None:
    """O coração da issue: cada pergunta é sintetizada UMA vez, para sempre, para todos os apps."""
    client = _client(_ok(), _ok())
    store = MemoryStore()

    first = await synthesize_speech(
        QUESTION, language="pt-BR", settings=_settings(), client=client, store=store
    )
    second = await synthesize_speech(
        QUESTION, language="pt-BR", settings=_settings(), client=client, store=store
    )

    assert client.post.await_count == 1  # a ElevenLabs foi chamada UMA vez
    assert first.cached is False
    assert second.cached is True
    assert second.audio == first.audio
    assert store.writes == 1


async def test_o_cache_sobrevive_ao_processo_porque_mora_no_bucket() -> None:
    # Um worker frio (store novo, mesmo bucket) ainda acha o objeto: é isto que o LRU
    # em processo do project_health/translation_helper NÃO faz.
    store = MemoryStore()
    await synthesize_speech(
        QUESTION, language="pt-BR", settings=_settings(), client=_client(_ok()), store=store
    )

    cold = MemoryStore()
    cold.objects = dict(store.objects)  # o bucket é o mesmo; o processo, não
    client = _client(_ok())

    result = await synthesize_speech(
        QUESTION, language="pt-BR", settings=_settings(), client=client, store=cold
    )

    assert client.post.await_count == 0
    assert result.cached is True


async def test_a_chave_e_enderecada_por_conteudo_voz_e_modelo() -> None:
    store = MemoryStore()
    await synthesize_speech(
        QUESTION, language="pt-BR", settings=_settings(), client=_client(_ok()), store=store
    )

    key = next(iter(store.objects))
    assert key == cache_key(QUESTION, voice_id=VOICES["pt-BR"], model="eleven_multilingual_v2")
    assert key.startswith(f"tts/{VOICES['pt-BR']}/eleven_multilingual_v2/")
    assert key.endswith(".mp3")


async def test_textos_diferentes_sao_clipes_diferentes() -> None:
    store = MemoryStore()
    client = _client(_ok(b"um"), _ok(b"dois"))

    await synthesize_speech(
        "primeira", language="pt-BR", settings=_settings(), client=client, store=store
    )
    await synthesize_speech(
        "segunda", language="pt-BR", settings=_settings(), client=client, store=store
    )

    assert client.post.await_count == 2
    assert len(store.objects) == 2


async def test_o_mesmo_texto_em_outro_idioma_usa_outra_voz_e_outro_clipe() -> None:
    store = MemoryStore()
    client = _client(_ok(b"pt"), _ok(b"en"))

    await synthesize_speech(
        QUESTION, language="pt-BR", settings=_settings(), client=client, store=store
    )
    await synthesize_speech(
        QUESTION, language="en-US", settings=_settings(), client=client, store=store
    )

    assert client.post.await_count == 2
    assert len(store.objects) == 2
    urls = [call.args[0] for call in client.post.await_args_list]
    assert VOICES["pt-BR"] in urls[0]
    assert VOICES["en-US"] in urls[1]
    assert VOICES["pt-BR"] != VOICES["en-US"]  # vozes NATIVAS, não uma multilíngue só


async def test_idioma_sem_voz_configurada_e_erro_explicito() -> None:
    # Silenciosamente cair numa voz de outro idioma sairia ininteligível.
    with pytest.raises(ValidationError):
        await synthesize_speech(
            QUESTION, language="ja-JP", settings=_settings(), client=_client(), store=MemoryStore()
        )


async def test_resolve_voice_aceita_a_lingua_base() -> None:
    assert resolve_voice("pt") == VOICES["pt-BR"]
    assert resolve_voice("en") == VOICES["en-US"]


async def test_texto_vazio_e_erro() -> None:
    with pytest.raises(ValidationError):
        await synthesize_speech(
            "   ", language="pt-BR", settings=_settings(), client=_client(), store=MemoryStore()
        )


async def test_falha_da_elevenlabs_vira_erro_de_negocio_e_nao_grava_nada() -> None:
    store = MemoryStore()

    with pytest.raises(ValidationError):
        await synthesize_speech(
            QUESTION,
            language="pt-BR",
            settings=_settings(),
            client=_client(_err(429)),
            store=store,
        )

    assert store.writes == 0  # nada de meio-clipe no cache


async def test_sem_chave_de_api_e_erro_de_configuracao() -> None:
    with pytest.raises(ValidationError):
        await synthesize_speech(
            QUESTION,
            language="pt-BR",
            settings=_settings(elevenlabs_api_key=""),
            client=_client(),
            store=MemoryStore(),
        )
