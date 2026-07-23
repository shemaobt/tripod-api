"""Platform translation to English, behind one callable.

The provider is deliberately swappable (the issue's "provider TBD"): today it is the same
Gemini client `services/i18n/translate_content.py` already uses, so nothing new is
installed and nothing new has to be paid for.

What comes out is a DRAFT. It is never merged into an artifact server-side — a bilingual
human confirms it in the SPA first (PRD v2 §1.1, §12).
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from google import genai

from app.core.config import Settings, get_settings
from app.core.exceptions import UpstreamServiceError, ValidationError
from app.services.platform.voices import language_hint

logger = logging.getLogger(__name__)

TRANSLATION_MODEL = "gemini-3-flash-preview"

#: Spoken-answer languages we can name for the model. An unlisted code is passed through as
#: itself rather than refused — naming the language is a prompt nicety, not a gate.
LANGUAGE_NAMES: dict[str, str] = {"pt": "Brazilian Portuguese", "en": "English"}

TRANSLATION_PROMPT = """\
Translate the following {language_name} text into English.

It is a transcript of a person speaking, so it may be informal, hesitant or unfinished.
Translate what is there — do not summarize it, do not complete it, do not explain it, and
do not add anything that was not said. Return the translation only, with no commentary.

Text:
{text}
"""


class Translator(Protocol):
    """The provider seam: swapping the model out is one callable."""

    async def __call__(self, text: str, *, source_language: str) -> str: ...


async def translate_to_english(
    text: str,
    *,
    source_language: str,
    settings: Settings | None = None,
    client: Any | None = None,
) -> str:
    """Translate `text` from `source_language` (BCP-47 locale) into English.

    Already-English text and empty text come straight back: every call is billed, and the
    cheapest translation is the one that never leaves.
    """
    base = language_hint(source_language)
    if base == "en" or not text.strip():
        return text.strip()

    cfg = settings or get_settings()
    if not cfg.google_api_key:
        raise ValidationError("GOOGLE_API_KEY is not configured")

    prompt = TRANSLATION_PROMPT.format(
        language_name=LANGUAGE_NAMES.get(base, source_language), text=text
    )
    provider = client or genai.Client(api_key=cfg.google_api_key)
    try:
        response = await provider.aio.models.generate_content(
            model=TRANSLATION_MODEL, contents=prompt
        )
    except Exception as exc:
        logger.warning("Gemini translation failed: %s", exc)
        raise UpstreamServiceError(f"Translation failed: {exc}") from exc

    translation = str(response.text or "").strip()
    if not translation:
        # An empty draft is indistinguishable from a silent recording, and would be
        # confirmed as one. Fail the answer instead and let it be retried.
        raise UpstreamServiceError("Translation returned empty text")

    logger.info(
        "platform translation: model=%s source=%s chars_in=%d chars_out=%d",
        TRANSLATION_MODEL,
        source_language,
        len(text),
        len(translation),
    )
    return translation
