"""Voice + language hint map for the project-health interview facilitator.

A single ElevenLabs multilingual voice is used for all six supported UI
locales. Override `MULTILINGUAL_VOICE_ID` to swap voices globally.
"""

MULTILINGUAL_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Sarah — warm multilingual female

LANGUAGE_HINTS: dict[str, str] = {
    "en": "en",
    "pt": "pt",
    "es": "es",
    "fr": "fr",
    "id": "id",
    "sw": "sw",
}


def resolve_language_hint(language: str | None) -> str | None:
    if not language:
        return None
    return LANGUAGE_HINTS.get(language.lower())
