from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2


async def call_llm(
    prompt: str,
    *,
    output_schema: type[BaseModel] | None = None,
    settings: Settings | None = None,
) -> Any:
    settings = settings or get_settings()
    llm = ChatGoogleGenerativeAI(
        model=settings.google_llm_model,
        google_api_key=settings.google_api_key,
        temperature=0,
        max_output_tokens=65536,
    )

    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if output_schema:
                structured = llm.with_structured_output(output_schema)
                return await structured.ainvoke(prompt)
            result = await llm.ainvoke(prompt)
            return result.content
        except Exception as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY**attempt
                logger.warning(
                    "LLM call attempt %d/%d failed (%s), retrying in %ds...",
                    attempt,
                    MAX_RETRIES,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error("LLM call failed after %d attempts: %s", MAX_RETRIES, exc)

    assert last_exc is not None
    raise last_exc
