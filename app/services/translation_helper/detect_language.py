from __future__ import annotations

import logging

from langdetect import DetectorFactory, LangDetectException, detect_langs

logger = logging.getLogger(__name__)

# langdetect uses randomness by default — pin the seed so the same input
# always yields the same detection result.
DetectorFactory.seed = 0

# ISO 639-1 → the BCP-47 keys our synthesize_speech VOICE_MAP uses.
# langdetect emits some Chinese variants as "zh-cn" / "zh-tw" already.
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
    """Best-effort BCP-47 language detection for TTS routing.

    Returns one of the keys in `synthesize_speech.VOICE_MAP`. Falls back to
    `default` when the text is too short, when detection raises, when the
    top candidate's probability is below `MIN_CONFIDENCE`, or when the
    detected language has no voice mapping.
    """
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
