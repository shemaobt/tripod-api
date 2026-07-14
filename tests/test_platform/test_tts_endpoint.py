from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

from tests.baker import make_user
from tests.test_platform.conftest import auth_header

MP3 = b"\xff\xfb\x90fake-mpeg-frame"
QUESTION = "Onde essa história acontece?"


@dataclass(frozen=True)
class _Speech:
    audio: bytes = MP3
    mime_type: str = "audio/mpeg"
    etag: str = "abc123"
    cached: bool = False


def _synth(**over: object) -> AsyncMock:
    return AsyncMock(return_value=_Speech(**over))  # type: ignore[arg-type]


async def test_devolve_audio_mpeg_cru_para_usuario_autenticado(db_session, client) -> None:
    # Bytes crus, NÃO base64-em-JSON: um envelope JSON obrigaria um DTO novo na camada
    # CONGELADA do SPA (contracts/), e infla 33% um corpo de ~100 KB.
    user = await make_user(db_session)
    headers = await auth_header(db_session, user)

    with patch("app.api.platform.tts.synthesize_speech", _synth()):
        res = await client.post(
            "/api/platform/tts/speak",
            json={"text": QUESTION, "language": "pt-BR"},
            headers=headers,
        )

    assert res.status_code == 200
    assert res.headers["content-type"].startswith("audio/mpeg")
    assert res.content == MP3
    assert res.headers["etag"] == "abc123"


async def test_qualquer_usuario_autenticado_entra_sem_app_key(db_session, client) -> None:
    # A plataforma não pertence a nenhum app: o usuário NÃO tem papel em app nenhum
    # (nenhum make_user_app_role) e mesmo assim é atendido — é o precedente do /api/uploads.
    user = await make_user(db_session)
    headers = await auth_header(db_session, user)

    with patch("app.api.platform.tts.synthesize_speech", _synth()):
        res = await client.post(
            "/api/platform/tts/speak",
            json={"text": QUESTION, "language": "en-US"},
            headers=headers,
        )

    assert res.status_code == 200


async def test_sinaliza_quando_o_clipe_veio_do_cache(db_session, client) -> None:
    # O aquecimento do cache precisa saber se bateu na ElevenLabs ou no bucket.
    user = await make_user(db_session)
    headers = await auth_header(db_session, user)

    with patch("app.api.platform.tts.synthesize_speech", _synth(cached=True)):
        res = await client.post(
            "/api/platform/tts/speak",
            json={"text": QUESTION, "language": "pt-BR"},
            headers=headers,
        )

    assert res.headers["x-tts-cached"] == "1"


async def test_anonimo_e_barrado(client) -> None:
    res = await client.post("/api/platform/tts/speak", json={"text": QUESTION, "language": "pt-BR"})

    assert res.status_code in (401, 403)


async def test_texto_vazio_e_422(db_session, client) -> None:
    user = await make_user(db_session)
    headers = await auth_header(db_session, user)

    res = await client.post(
        "/api/platform/tts/speak", json={"text": "", "language": "pt-BR"}, headers=headers
    )

    assert res.status_code == 422


async def test_texto_longo_demais_e_422(db_session, client) -> None:
    user = await make_user(db_session)
    headers = await auth_header(db_session, user)

    res = await client.post(
        "/api/platform/tts/speak",
        json={"text": "a" * 3001, "language": "pt-BR"},
        headers=headers,
    )

    assert res.status_code == 422
