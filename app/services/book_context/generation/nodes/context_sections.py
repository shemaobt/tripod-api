from __future__ import annotations

import json
import logging
from typing import Any

from app.services.book_context.generation.llm import call_llm
from app.services.book_context.generation.nodes.utils import summarize_participants
from app.services.book_context.generation.schemas import (
    ContextSectionsNoPlacesSchema,
    ContextSectionsSchema,
    PlacesRegisterSchema,
)
from app.services.book_context.generation.state import BCDGenerationState

logger = logging.getLogger(__name__)

PLACE_BATCH_SIZE = 60

CONTEXT_SECTIONS_PROMPT = """\
You are a biblical scholar completing the Book Context Document for {book_name} ({genre}).

Structural outline:
{outline}

Participant register:
{participants}

Discourse threads:
{threads}

BHSA linguistic data summary:
{bhsa_summary}

## Place Entities (AUTHORITATIVE — pre-classified from BHSA)

The following entities have been classified as places by the BHSA linguistic \
database (via the `nametype` feature). Each entity includes: name, english_gloss, \
entity_type, entry_verse, exit_verse, appears_in, and appearance_count.

{place_entities}

Generate the remaining sections:

1. **Theological Spine**: 2-4 paragraphs describing the theological arc of the book. \
How does God act? What theological themes run through the narrative? What is the book's \
contribution to the canon?

2. **Places**: Create an entry for EACH place entity listed above. \
All entities have already been classified as places — do not skip any.
For each place:
- name: Copy EXACTLY from the entity data
- english_gloss: Copy from the entity data. If empty, provide the English \
translation of the Hebrew name.
- entity_type: Copy EXACTLY from the entity data
- first_appears: Copy EXACTLY from the entity data (use entry_verse)
- type: city, region, field, country, etc.
- meaning_and_function: The place's significance in the narrative
- appears_in: Copy the ENTIRE appears_in list EXACTLY from the entity data
- appearance_count: Copy EXACTLY from the entity data

CRITICAL: The name, english_gloss, entity_type, first_appears, appears_in, and \
appearance_count fields are static and MUST match the entity data exactly. \
Do NOT invent places not in the list.

3. **Objects**: Significant physical objects, animals, or temporal markers from the text. \
These are typically NOT proper nouns, so they won't be in the entity list. \
For each: name (in Hebrew if the original text uses a Hebrew term), english_gloss \
(English translation of the name — if the name is already English, repeat it), \
first_appears, what_it_is, meaning_across_scenes, appears_in.

4. **Institutions**: Cultural/legal institutions referenced in the text. \
These are typically NOT proper nouns, so they won't be in the entity list. \
For each: name (in Hebrew if the original text uses a Hebrew term), english_gloss \
(English translation of the name — if the name is already English, repeat it), \
first_invoked (chapter/verse), what_it_is, role_in_book, appears_in.

5. **Genre Context**:
- primary_genre: The primary literary genre
- sub_genres: List of secondary genres present
- narrative_voice: Description of the narrative perspective
- temporal_setting: When the events take place
- audience_positioning: How the text positions the reader/listener

6. **Maintenance Notes**:
- generation_notes: Brief note about how this document was generated
- known_limitations: List of known limitations or areas that may need human review
"""

CONTEXT_NO_PLACES_PROMPT = """\
You are a biblical scholar completing the Book Context Document for {book_name} ({genre}).

Structural outline:
{outline}

Participant register:
{participants}

Discourse threads:
{threads}

BHSA linguistic data summary:
{bhsa_summary}

Generate the following sections (places are handled separately):

1. **Theological Spine**: 2-4 paragraphs describing the theological arc of the book. \
How does God act? What theological themes run through the narrative? What is the book's \
contribution to the canon?

2. **Objects**: Significant physical objects, animals, or temporal markers from the text. \
For each: name (in Hebrew if the original text uses a Hebrew term), english_gloss \
(English translation of the name — if the name is already English, repeat it), \
first_appears, what_it_is, meaning_across_scenes, appears_in.

3. **Institutions**: Cultural/legal institutions referenced in the text. \
For each: name (in Hebrew if the original text uses a Hebrew term), english_gloss \
(English translation of the name — if the name is already English, repeat it), \
first_invoked (chapter/verse), what_it_is, role_in_book, appears_in.

4. **Genre Context**:
- primary_genre: The primary literary genre
- sub_genres: List of secondary genres present
- narrative_voice: Description of the narrative perspective
- temporal_setting: When the events take place
- audience_positioning: How the text positions the reader/listener

5. **Maintenance Notes**:
- generation_notes: Brief note about how this document was generated
- known_limitations: List of known limitations or areas that may need human review
"""

PLACES_BATCH_PROMPT = """\
You are a biblical scholar creating place entries for {book_name}.

Create an entry for EACH place entity listed below. \
All entities have already been classified as places — do not skip any.

For each place:
- name: Copy EXACTLY from the entity data
- english_gloss: Copy from the entity data. If empty, provide the English \
translation of the Hebrew name.
- entity_type: Copy EXACTLY from the entity data
- first_appears: Copy EXACTLY from the entity data (use entry_verse)
- type: city, region, field, country, etc.
- meaning_and_function: The place's significance in the narrative
- appears_in: Copy the ENTIRE appears_in list EXACTLY from the entity data
- appearance_count: Copy EXACTLY from the entity data

CRITICAL: The name, english_gloss, entity_type, first_appears, appears_in, and \
appearance_count fields are static and MUST match the entity data exactly. \
Do NOT invent places not in the list.

## Place Entities

{place_entities}
"""


def _build_shared_context(state: BCDGenerationState) -> dict[str, str]:
    return {
        "book_name": state["book_name"],
        "genre": state["genre"],
        "outline": json.dumps(state.get("structural_outline", {}), indent=2),
        "participants": summarize_participants(state.get("participant_register", [])),
        "threads": json.dumps(state.get("discourse_threads", []), indent=2),
        "bhsa_summary": state.get("bhsa_summary", ""),
    }


async def _generate_place_batch(
    entities: list[dict[str, Any]],
    book_name: str,
) -> list[dict[str, Any]]:
    prompt = PLACES_BATCH_PROMPT.format(
        book_name=book_name,
        place_entities=json.dumps(entities, indent=2),
    )
    result = await call_llm(prompt, output_schema=PlacesRegisterSchema)
    return [p.model_dump() for p in result.places]


async def generate_context_sections(
    state: BCDGenerationState,
) -> dict[str, Any]:
    bhsa_entities = state.get("bhsa_entities", [])
    place_entities = [e for e in bhsa_entities if e.get("entity_type") == "place"]

    if len(place_entities) <= PLACE_BATCH_SIZE:
        ctx = _build_shared_context(state)
        prompt = CONTEXT_SECTIONS_PROMPT.format(
            **ctx,
            place_entities=json.dumps(place_entities, indent=2),
        )
        if state.get("user_feedback"):
            prompt += "\n\n## User Feedback (address these concerns)\n" + state["user_feedback"]
        result = await call_llm(prompt, output_schema=ContextSectionsSchema)
        return {
            "theological_spine": result.theological_spine,
            "places": [p.model_dump() for p in result.places],
            "objects": [o.model_dump() for o in result.objects],
            "institutions": [i.model_dump() for i in result.institutions],
            "genre_context": result.genre_context.model_dump(),
            "maintenance_notes": result.maintenance_notes.model_dump(),
        }

    logger.info(
        "Splitting %d place entities into batches of ~%d",
        len(place_entities),
        PLACE_BATCH_SIZE,
    )

    ctx = _build_shared_context(state)
    no_places_prompt = CONTEXT_NO_PLACES_PROMPT.format(**ctx)
    if state.get("user_feedback"):
        no_places_prompt += (
            "\n\n## User Feedback (address these concerns)\n" + state["user_feedback"]
        )
    sections = await call_llm(no_places_prompt, output_schema=ContextSectionsNoPlacesSchema)

    batches = [
        place_entities[i : i + PLACE_BATCH_SIZE]
        for i in range(0, len(place_entities), PLACE_BATCH_SIZE)
    ]
    all_places: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for idx, batch in enumerate(batches, 1):
        logger.info(
            "Processing place batch %d/%d (%d entities)",
            idx,
            len(batches),
            len(batch),
        )
        batch_result = await _generate_place_batch(batch, state["book_name"])
        for p in batch_result:
            name = p.get("name", "")
            if name not in seen_names:
                seen_names.add(name)
                all_places.append(p)

    return {
        "theological_spine": sections.theological_spine,
        "places": all_places,
        "objects": [o.model_dump() for o in sections.objects],
        "institutions": [i.model_dump() for i in sections.institutions],
        "genre_context": sections.genre_context.model_dump(),
        "maintenance_notes": sections.maintenance_notes.model_dump(),
    }
