from __future__ import annotations

import json
import logging
from typing import Any

from app.services.book_context.generation.llm import call_llm
from app.services.book_context.generation.schemas import ParticipantRegisterSchema
from app.services.book_context.generation.state import BCDGenerationState

logger = logging.getLogger(__name__)

BATCH_SIZE = 80

PARTICIPANT_PROMPT = """\
You are a biblical scholar creating a participant register for {book_name}.

Structural outline of the book:
{outline}

BHSA linguistic data summary:
{bhsa_summary}

## Person Entities (AUTHORITATIVE — pre-classified from BHSA)

The following entities have been classified as persons/groups by the BHSA linguistic \
database (via the `nametype` feature). Each entity includes: name, english_gloss, \
entity_type, entry_verse, exit_verse, appears_in, and appearance_count.

{person_entities}

## Your Task

Create a participant entry for EACH person entity listed above. \
All entities have already been classified as persons — do not skip any.

For each participant:
- name: Copy EXACTLY from the entity data
- english_gloss: Copy from the entity data. If empty, provide the English \
translation of the Hebrew name.
- entity_type: Copy EXACTLY from the entity data
- type: "named" for individuals, "group" for groups, "divine" for God/YHWH
- entry_verse: Copy EXACTLY from the entity data (do NOT change)
- exit_verse: Copy EXACTLY from the entity data (do NOT change)
- appears_in: Copy the ENTIRE appears_in list EXACTLY from the entity data
- appearance_count: Copy EXACTLY from the entity data
- role_in_book: Their narrative role (protagonist, antagonist, supporting, etc.)
- relationships: List of relationship descriptions
- what_audience_knows_at_entry: What the audience knows when they first appear
- arc: List of {{at: {{chapter, verse}}, state: "description"}} tracking their development
- status_at_end: Their state at the book's conclusion

CRITICAL RULES:
1. Create an entry for EVERY person entity in the list — do NOT skip any.
2. Do NOT invent new participants not in the list.
3. The name, english_gloss, entity_type, entry_verse, exit_verse, appears_in, \
and appearance_count MUST be copied exactly — these are static fields.
4. Your enrichment is limited to: type, role_in_book, relationships, \
what_audience_knows_at_entry, arc, and status_at_end.
"""


async def _generate_batch(
    entities: list[dict[str, Any]],
    state: BCDGenerationState,
    outline_json: str,
) -> list[dict[str, Any]]:
    prompt = PARTICIPANT_PROMPT.format(
        book_name=state["book_name"],
        outline=outline_json,
        bhsa_summary=state.get("bhsa_summary", ""),
        person_entities=json.dumps(entities, indent=2),
    )
    if state.get("user_feedback"):
        prompt += (
            "\n\n## User Feedback (address these concerns in your output)\n"
            + state["user_feedback"]
        )
    result = await call_llm(prompt, output_schema=ParticipantRegisterSchema)
    return [p.model_dump() for p in result.participants]


async def generate_participants(
    state: BCDGenerationState,
) -> dict[str, list[dict[str, Any]]]:
    bhsa_entities = state.get("bhsa_entities", [])
    person_entities = [e for e in bhsa_entities if e.get("entity_type") in ("person", "ambiguous")]

    if len(person_entities) <= BATCH_SIZE:
        participants = await _generate_batch(
            person_entities,
            state,
            json.dumps(state.get("structural_outline", {}), indent=2),
        )
        return {"participant_register": participants}

    batches = [
        person_entities[i : i + BATCH_SIZE] for i in range(0, len(person_entities), BATCH_SIZE)
    ]
    logger.info(
        "Splitting %d entities into %d batches of ~%d",
        len(person_entities),
        len(batches),
        BATCH_SIZE,
    )

    outline_json = json.dumps(state.get("structural_outline", {}), indent=2)
    all_participants: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for idx, batch in enumerate(batches, 1):
        logger.info(
            "Processing participant batch %d/%d (%d entities)",
            idx,
            len(batches),
            len(batch),
        )
        batch_result = await _generate_batch(batch, state, outline_json)
        for p in batch_result:
            name = p.get("name", "")
            if name not in seen_names:
                seen_names.add(name)
                all_participants.append(p)
            else:
                logger.warning("Skipping duplicate participant: %s", name)

    return {"participant_register": all_participants}
