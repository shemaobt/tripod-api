from __future__ import annotations

import json
import logging
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from qdrant_client import AsyncQdrantClient

from app.core.config import Settings, get_settings
from app.models.rag import RagNamespace
from app.services.bhsa import loader as bhsa_loader
from app.services.rag.query import query as rag_query

logger = logging.getLogger(__name__)

GENERATION_SYSTEM_PROMPT = """\
You are a biblical text analyst specializing in the Tripod Method for Oral Bible Translation (OBT).
Your task is to generate a Prose Meaning Map (PMM) for a given biblical passage.

A PMM has three levels:

**Level 1 — The Arc:** A single block of continuous prose (no bullets, no numbered lists)
capturing the overall narrative arc of the passage. Minimum 80 words.

**Level 2 — Scenes:** One scene per logical unit (verse range). Each scene has:
- 2A People: Every person present (Name, Role, Relationship, Wants, Carries)
- 2B Places: Every location (Name, Role, Type, Meaning, Effect on scene)
- 2C Objects & Elements: Physical objects/durations/natural elements \
(Name, What it is, Function in scene, Signals) plus Significant Absence
- 2D What Happens: Prose narrative of scene events (minimum 15 words)
- 2E Communicative Purpose: Why this scene exists (minimum 3 sentences, 10 words)

**Level 3 — Propositions:** One per verse. Each is Q&A pairs.
- First question MUST be "What happens?"
- Additional questions decompose embedded content
- Answers should be semantic inventory, NOT commentary or interpretation

You MUST output valid JSON matching this exact schema:
{
  "level_1": { "arc": "string" },
  "level_2_scenes": [{
    "scene_number": 1,
    "verses": "1-3",
    "title": "string",
    "people": [{ "name": "", "role": "", "relationship": "", "wants": "", "carries": "" }],
    "places": [{ "name": "", "role": "", "type": "", "meaning": "", "effect_on_scene": "" }],
    "objects": [{ "name": "", "what_it_is": "", "function_in_scene": "", "signals": "" }],
    "significant_absence": "",
    "what_happens": "",
    "communicative_purpose": ""
  }],
  "level_3_propositions": [{
    "proposition_number": 1,
    "verse": "1",
    "content": [{ "question": "What happens?", "answer": "" }]
  }]
}

IMPORTANT:
- Output ONLY the JSON object, no markdown fences, no explanation before or after.
- Every field must be populated.
- Answers must NOT contain commentary words (significant, important, notably, etc.)
- Answers must NOT contain performance frames (behold, and then, etc.)
"""


def _build_generation_prompt(
    reference: str,
    bhsa_data: dict[str, Any] | None,
    rag_context: str | None,
) -> str:
    parts = [GENERATION_SYSTEM_PROMPT]

    parts.append(f"\n## Passage: {reference}\n")

    if bhsa_data and bhsa_data.get("clauses"):
        parts.append("## Hebrew Linguistic Data (BHSA)\n")
        for clause in bhsa_data["clauses"]:
            clause_text = clause.get("text_plain", "")
            clause_type = clause.get("clause_type", "")
            gloss = clause.get("gloss", "")
            parts.append(f"- [{clause_type}] {clause_text} — {gloss}")
        parts.append("")

    if rag_context:
        parts.append("## Methodology Reference\n")
        parts.append(rag_context)
        parts.append("")

    parts.append("Now generate the complete Prose Meaning Map as a single JSON object.\n")

    return "\n".join(parts)


def _parse_llm_output(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    return json.loads(text)


def _empty_map() -> dict[str, Any]:
    return {
        "level_1": {"arc": ""},
        "level_2_scenes": [],
        "level_3_propositions": [],
    }


async def generate_meaning_map(
    reference: str,
    *,
    settings: Settings | None = None,
    qdrant_client: AsyncQdrantClient | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()

    bhsa_data: dict[str, Any] | None = None
    if bhsa_loader.get_status()["is_loaded"]:
        try:
            bhsa_data = bhsa_loader.fetch_passage(reference)
        except Exception as e:
            logger.warning("BHSA extraction failed for %s: %s", reference, e)

    rag_context: str | None = None
    if qdrant_client:
        try:
            rag_result = await rag_query(
                qdrant_client,
                RagNamespace.MEANING_MAP_DOCS,
                f"How to create a Prose Meaning Map for {reference}",
                settings=settings,
            )
            if rag_result.answer:
                rag_context = rag_result.answer
        except Exception as e:
            logger.warning("RAG query failed for %s: %s", reference, e)

    prompt = _build_generation_prompt(reference, bhsa_data, rag_context)

    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.google_llm_model,
            google_api_key=settings.google_api_key,
        )
        response = await llm.ainvoke(prompt)
        content = response.content
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )
        return _parse_llm_output(content)
    except Exception as e:
        logger.error("LLM generation failed for %s: %s", reference, e)
        return _empty_map()
