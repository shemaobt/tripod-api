from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.book_context import BCDGenerationLog
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

## Common Noun Candidates (BHSA-extracted substantives — for groups/roles only)

The following common nouns were extracted from the BHSA. Inspect this list to \
identify HUMAN COLLECTIVE ROLES that participate in the narrative as groups (e.g. \
elders, women of Bethlehem, reapers, servants, kinsmen). Each candidate includes: \
lemma (Hebrew), lemma_ascii, english_gloss, sp ("subs" / "adjv" / "verb"), \
appearance_count, top_functions, first_appears, sample_appears_in.

ONLY substantives (`sp == "subs"`) referring to human roles/groups should become \
participant entries from this list. Verbs and abstract substantives must be \
ignored here (they are processed in other sections of the document).

{common_nouns}

## Your Task

Produce participant entries from BOTH sources above:

### Source A — Person Entities (proper nouns)
Create an entry for EACH person entity listed above. \
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

### Source B — Common Noun Groups/Roles
For each substantive candidate above that denotes a HUMAN COLLECTIVE ROLE \
narratively significant in the book, add a participant entry with:
- name: the Hebrew lemma (lemma field) from the candidate
- english_gloss: the candidate's english_gloss
- entity_type: "person_common"
- type: "group"
- entry_verse: copy from candidate's first_appears
- exit_verse: leave null
- appears_in: copy from candidate's sample_appears_in
- appearance_count: copy from candidate's appearance_count
- role_in_book, relationships, what_audience_knows_at_entry, arc, status_at_end: \
your scholarly enrichment based on the narrative.

CRITICAL RULES:
1. For Source A: create an entry for EVERY person entity in the list — do NOT skip any.
2. For Source A: do NOT invent new proper-noun participants not in the list. \
The name, english_gloss, entity_type, entry_verse, exit_verse, appears_in, \
and appearance_count MUST be copied exactly — these are static fields.
3. For Source B: you MUST select from the Common Noun Candidates list — \
do NOT invent groups/roles not in the list. Only include candidates that \
clearly denote human collective roles (skip objects, places, abstract concepts, verbs).
4. Your enrichment for both sources is limited to: type, role_in_book, \
relationships, what_audience_knows_at_entry, arc, and status_at_end.
"""


async def _generate_batch(
    entities: list[dict[str, Any]],
    state: BCDGenerationState,
    outline_json: str,
    common_nouns_json: str,
) -> list[dict[str, Any]]:
    prompt = PARTICIPANT_PROMPT.format(
        book_name=state["book_name"],
        outline=outline_json,
        bhsa_summary=state.get("bhsa_summary", ""),
        person_entities=json.dumps(entities, indent=2),
        common_nouns=common_nouns_json,
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
    *,
    db: AsyncSession | None = None,
    log: BCDGenerationLog | None = None,
) -> dict[str, list[dict[str, Any]]]:
    bhsa_entities = state.get("bhsa_entities", [])
    person_entities = [e for e in bhsa_entities if e.get("entity_type") in ("person", "ambiguous")]
    common_nouns = [
        c for c in state.get("bhsa_common_nouns", []) if c.get("sp") == "subs"
    ]
    common_nouns_json = json.dumps(common_nouns, indent=2, ensure_ascii=False)

    if len(person_entities) <= BATCH_SIZE:
        participants = await _generate_batch(
            person_entities,
            state,
            json.dumps(state.get("structural_outline", {}), indent=2),
            common_nouns_json,
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
        if db and log:
            log.output_summary = f"Batch {idx}/{len(batches)} ({len(batch)} entities)"
            await db.commit()

        batch_result = await _generate_batch(batch, state, outline_json, common_nouns_json)
        for p in batch_result:
            name = p.get("name", "")
            if name not in seen_names:
                seen_names.add(name)
                all_participants.append(p)
            else:
                logger.warning("Skipping duplicate participant: %s", name)

    return {"participant_register": all_participants}
