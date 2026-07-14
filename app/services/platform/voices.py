"""Mapa idioma → voz da plataforma.

Inline no código de propósito (decisão do dono): a voz é uma escolha de produto, feita de
ouvido, não configuração de ambiente — quem a troca precisa ouvir o resultado e abrir um PR.

**Uma voz NATIVA por idioma**, não uma multilíngue só. A ElevenLabs avisa que uma voz
"retains its unique characteristics *and accent*" em qualquer língua que fale: a voz única
(`EXAVITQu4vr4xnSDxMaL`, que o project_health e o translation_helper usam hoje) lê inglês
com sotaque brasileiro, e vice-versa. Numa ferramenta cuja tese é soar humana, isso pesa.
"""

from app.core.exceptions import ValidationError

PT_BR = "aU2vcrnwi348Gnc2Y1si"
EN_US = "gfRt6Z3Z8aTbpLfexQ7N"

#: Locale BCP-47 → `voice_id`. Aceita a língua base como apelido do locale principal.
VOICES: dict[str, str] = {
    "pt-BR": PT_BR,
    "pt": PT_BR,
    "en-US": EN_US,
    "en": EN_US,
}


def resolve_voice(language: str) -> str:
    """A voz do idioma pedido.

    Erra explicitamente num idioma sem voz configurada em vez de emprestar a de outro:
    uma voz pt-BR lendo japonês sai ininteligível, e um silêncio confuso é pior que um
    erro claro.
    """
    voice = VOICES.get(language) or VOICES.get(language.split("-")[0])
    if voice is None:
        raise ValidationError(f"No voice configured for language {language!r}")
    return voice


def language_hint(language: str) -> str:
    """A língua base (`pt-BR` → `pt`), como a ElevenLabs espera em `language_code`."""
    return language.split("-")[0].lower()
