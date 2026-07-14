from fastapi import APIRouter, Depends, Response

from app.core.auth_middleware import get_current_user
from app.db.models.auth import User
from app.models.platform import TtsSpeakRequest
from app.services.platform.tts import synthesize_speech

router = APIRouter()


@router.post(
    "/tts/speak",
    response_class=Response,
    responses={200: {"content": {"audio/mpeg": {}}, "description": "MP3 sintetizado"}},
)
async def speak_endpoint(
    payload: TtsSpeakRequest,
    _: User = Depends(get_current_user),
) -> Response:
    """Fala um texto: devolve o MP3 CRU (não base64-em-JSON).

    Base64 infla 33% um corpo de ~100 KB e força um parse de JSON para chegar em bytes.
    Pior: do lado do SPA, um envelope JSON obrigaria um DTO novo em `contracts/`, que lá é
    camada congelada com revisão humana obrigatória. Bytes crus mantêm o consumidor simples.
    """
    speech = await synthesize_speech(payload.text, language=payload.language)
    return Response(
        content=speech.audio,
        media_type=speech.mime_type,
        headers={
            "ETag": speech.etag,
            # O conteúdo é endereçado por hash: mesma chave ⇒ mesmos bytes, sempre.
            "Cache-Control": "private, max-age=86400, immutable",
            # Deixa o aquecimento do cache observável: bateu no bucket ou na ElevenLabs?
            "X-Tts-Cached": "1" if speech.cached else "0",
        },
    )
