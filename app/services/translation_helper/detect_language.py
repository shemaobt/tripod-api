from __future__ import annotations

import logging

from langdetect import DetectorFactory, LangDetectException, detect_langs

logger = logging.getLogger(__name__)

DetectorFactory.seed = 0

_ISO_TO_VOICE_LANG: dict[str, str] = {
    "en": "en-US",
    "es": "es-ES",
    "fr": "fr-FR",
    "pt": "pt-BR",
    "de": "de-DE",
    "it": "it-IT",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "zh-cn": "zh-CN",
    "zh-tw": "zh-CN",
    "hi": "hi-IN",
    "ar": "ar-SA",
    "ru": "ru-RU",
    "nl": "nl-NL",
    "sv": "sv-SE",
    "da": "da-DK",
}

DEFAULT_LANGUAGE = "en-US"
MIN_CONFIDENCE = 0.85
MIN_TEXT_LEN_FOR_DETECT = 12


def detect_language_code(text: str, *, default: str = DEFAULT_LANGUAGE) -> str:
    """Return a BCP-47 voice key for `text`, falling back to `default`."""
    stripped = text.strip() if text else ""
    if len(stripped) < MIN_TEXT_LEN_FOR_DETECT:
        return default
    try:
        candidates = detect_langs(stripped)
    except LangDetectException:
        return default
    if not candidates:
        return default
    top = candidates[0]
    if top.prob < MIN_CONFIDENCE:
        return default
    return _ISO_TO_VOICE_LANG.get(top.lang, default)
