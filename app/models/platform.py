from pydantic import BaseModel, Field

#: A pergunta mais longa do Colar de Sons tem ~200 caracteres; o mesmo teto do project_health.
MAX_TTS_CHARS = 3000


class TtsSpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TTS_CHARS)
    #: Locale BCP-47 (`pt-BR`, `en-US`) — o mapa locale→voz vive em `services/platform/voices.py`.
    language: str = Field(min_length=2, max_length=16)
