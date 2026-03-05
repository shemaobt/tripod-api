from __future__ import annotations

import logging
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from qdrant_client import AsyncQdrantClient

from app.core.config import Settings, get_settings
from app.models.meaning_map import ProseMeaningMap
from app.models.rag import RagNamespace
from app.services.bhsa import loader as bhsa_loader
from app.services.rag.query import query as rag_query

logger = logging.getLogger(__name__)


class GenerationError(Exception):
    """Raised when a required generation data source is unavailable."""

GENERATION_PROMPT_TEMPLATE = """\
You are an expert biblical exegete and mapper for the "Tripod Method for AI-Assisted \
Oral Bible Translation." Your task is to produce a complete, flawless Bible Meaning Map \
for a given biblical passage.
You will be provided with the target pericope and its highly granular linguistic data \
from the BHSA (Biblia Hebraica Stuttgartensia Amstelodamensis) database. You must use \
this linguistic data as your absolute ground truth for the text's contents, participants, \
and event sequencing. Do not rely on standard English translations, as they introduce \
structural bias.
Produce the map in three distinct levels, adhering to the strict division of labor and \
formatting rules outlined below.

INPUT DATA:
Target Passage: {reference}

{bhsa_section}
{rag_section}

STEP 1: Level 1 — The Arc
Write one or two prose paragraphs giving the performer the "world" of the passage. \
You must address:
- The Arc/Shape: The emotional trajectory, pacing, and what the section accomplishes \
in the larger story.
- Theological Significance: How God acts (or conspicuously doesn't), and the \
theological weight.
- Temporal and Modal Register: You MUST explicitly state the register (e.g., \
"completed past narrative, moving forward in sequence," "gnomic/timeless," \
"imperative/procedural").

STEP 2: Level 2 — The Scenes
Divide the passage into natural episodes (typically 3-6 verses). For each scene, provide:
- Title: A one-sentence description.
- 2A — People: Every person present. List: Name, Role, Relationship, Wants, and \
Carries/Fears.
- 2B — Places: Every location (including transitional spaces/roads). List: Name, Role, \
Type, Meaning, and Effect on scene.
- 2C — Objects and Elements: Every physical thing, animal, duration of time. List: Name, \
What it is, Function, and What it signals. Explicitly note Significant Absences at the end.
- 2D — What Happens: A full prose description of actions, specific about cause and \
effect. Rule: Do not reproduce or paraphrase the biblical clauses sentence-by-sentence.
- 2E — Communicative Purpose: A mandatory prose paragraph (min. 3 sentences) explaining \
why the scene exists, what it establishes, and the emotional/theological weight the \
performer must carry.

STEP 3: Level 3 — The Propositions
Create one semantic inventory block for every single verse. Use the BHSA clause and \
phrase tags (Subj, Pred, Objc, Cmpl) to accurately map what occurs.

Strict Level 3 Rules:
- Question & Answer Format: The first line is always "What happens?" followed by an \
event label (e.g., a death, a departure, a speech act). Remaining lines use plain \
natural questions ("Who?", "To where?", "With whom?") based on the event.
- NO FINITE CLAUSES: The answer side of a line must NEVER contain a conjugated verb \
with its own subject. If an answer would naturally be a clause (e.g., "because the \
famine ended"), it is an embedded proposition. You must name the outer relation on one \
line, and decompose the inner content into sub-lines.
- Direct Naming: Never paraphrase proper names, place names, or specific concrete nouns \
(e.g., Bethlehem is Bethlehem, not "a town in Judah").
- No Commentary: Keep all emotional tone, theological notes, and performance frames \
(e.g., "And then", "Listen!") out of Level 3.
- Handling Speech Acts: Use two layers. The outer layer maps the speech act (e.g., \
"What she does with the words? blesses; releases"). The inner layer maps the content \
line-by-line, introduced by "What the words say — [ordinal/question]?". Never use \
commentary wrappers (e.g., avoid "a reminder that..." or "a promise to...").
- Manner & Attribute: If the BHSA data shows an explicit modifier/adjunct of manner, \
add a "How?" line. If it predicates a specific quality, add a "His/her/its condition?" \
line.

Format Example for Level 3:
  Proposition X — Verse Y
  What happens? a man emigrates temporarily
  Who? Elimelech
  From where? Bethlehem in Judah
  To where? the fields of Moab
  With whom? his wife Naomi; his two sons Mahlon and Kilion

Now, generate the complete Bible Meaning Map for {reference}.
"""


def _format_bhsa_clauses(clauses: list[dict[str, Any]]) -> str:
    """Format BHSA clause dicts into rich multi-line text for the LLM prompt."""
    lines: list[str] = []
    for c in clauses:
        line = (
            f"  Verse {c.get('verse', '?')} | [{c.get('clause_type', '')}] "
            f"{c.get('text', '')} — {c.get('gloss', '')}"
        )

        if c.get("lemma"):
            line += f" | verb: {c['lemma']} ({c.get('binyan', '?')}, {c.get('tense', '?')})"

        mainline = c.get("is_mainline", False)
        chain = c.get("chain_position", "?")
        line += f" | mainline: {mainline} | chain: {chain}"

        if c.get("subjects"):
            line += f" | subj: {', '.join(c['subjects'])}"
        if c.get("objects"):
            line += f" | obj: {', '.join(c['objects'])}"
        if c.get("names"):
            line += f" | names: {', '.join(c['names'])}"
        if c.get("has_ki"):
            line += " | has_ki: true"

        lines.append(line)
    return "\n".join(lines)


def _build_generation_prompt(
    reference: str,
    bhsa_data: dict[str, Any] | None,
    rag_context: str | None,
) -> str:
    bhsa_section = ""
    if bhsa_data and bhsa_data.get("clauses"):
        formatted = _format_bhsa_clauses(bhsa_data["clauses"])
        bhsa_section = f"BHSA Linguistic Data:\n{formatted}"

    rag_section = ""
    if rag_context:
        rag_section = f"Methodology Reference:\n{rag_context}"

    return GENERATION_PROMPT_TEMPLATE.format(
        reference=reference,
        bhsa_section=bhsa_section,
        rag_section=rag_section,
    )


async def generate_meaning_map(
    reference: str,
    *,
    settings: Settings | None = None,
    qdrant_client: AsyncQdrantClient | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()

    # --- BHSA (required) ---
    if not bhsa_loader.get_status()["is_loaded"]:
        raise GenerationError("BHSA data is not loaded. Contact an administrator.")

    try:
        bhsa_data = bhsa_loader.fetch_passage(reference)
    except Exception as e:
        raise GenerationError(f"BHSA extraction failed for {reference}: {e}") from e

    if not bhsa_data or not bhsa_data.get("clauses"):
        raise GenerationError(f"BHSA returned no clause data for {reference}.")

    # --- RAG (required) ---
    if qdrant_client is None:
        raise GenerationError("RAG service is not available. Contact an administrator.")

    try:
        rag_result = await rag_query(
            qdrant_client,
            RagNamespace.MEANING_MAP_DOCS,
            f"How to create a Bible Meaning Map for {reference}",
            settings=settings,
        )
    except Exception as e:
        raise GenerationError(f"RAG query failed for {reference}: {e}") from e

    if not rag_result.answer:
        raise GenerationError(f"RAG returned no methodology context for {reference}.")

    rag_context = rag_result.answer

    prompt = _build_generation_prompt(reference, bhsa_data, rag_context)

    # --- LLM ---
    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.google_llm_model,
            google_api_key=settings.google_api_key,
        )
        structured_llm = llm.with_structured_output(ProseMeaningMap)
        result = await structured_llm.ainvoke(prompt)
        return result.model_dump()
    except Exception as e:
        raise GenerationError(f"LLM generation failed: {e}") from e
