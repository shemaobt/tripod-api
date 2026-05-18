from __future__ import annotations

import json
import logging
from typing import Any, TypeVar, cast

from google import genai
from google.genai import types

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

FAST_MODEL = "gemini-3-flash-preview"
QUALITY_MODEL = "gemini-3-flash-preview"

T = TypeVar("T")


async def call_agent(
    *,
    system_prompt: str,
    user_content: str,
    model: str = FAST_MODEL,
    temperature: float = 0.4,
    max_output_tokens: int = 2000,
    settings: Settings | None = None,
) -> str:
    settings = settings or get_settings()
    client = genai.Client(api_key=settings.google_api_key)
    response = await client.aio.models.generate_content(
        model=model,
        contents=[{"role": "user", "parts": [{"text": user_content}]}],
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        ),
    )
    return response.text or ""


async def call_chat(
    *,
    system_prompt: str,
    contents: list[dict],
    model: str = QUALITY_MODEL,
    temperature: float = 0.6,
    max_output_tokens: int = 500,
    settings: Settings | None = None,
) -> str:
    settings = settings or get_settings()
    client = genai.Client(api_key=settings.google_api_key)
    response = await client.aio.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        ),
    )
    return response.text or ""


def safe_parse_json(text: str, fallback: T) -> T:
    if not text:
        return fallback
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.lstrip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    try:
        parsed: Any = json.loads(cleaned)
        return cast(T, parsed)
    except (json.JSONDecodeError, TypeError, ValueError):
        logger.warning("project_health agent JSON parse failed: %s", text[:200])
        return fallback
