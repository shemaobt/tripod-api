from __future__ import annotations

import json

from app.services.book_context.generation.llm import call_llm
from app.services.book_context.generation.schemas import ContextSectionsSchema
from app.services.book_context.generation.state import BCDGenerationState

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
- english_gloss: Copy EXACTLY from the entity data
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
For each: name, first_appears, what_it_is, meaning_across_scenes, appears_in.

4. **Institutions**: Cultural/legal institutions referenced in the text. \
These are typically NOT proper nouns, so they won't be in the entity list. \
For each: name, first_invoked (chapter/verse), what_it_is, role_in_book, appears_in.

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


async def generate_context_sections(state: BCDGenerationState) -> dict:
    bhsa_entities = state.get("bhsa_entities", [])

    # Pre-filter to place entities only
    place_entities = [e for e in bhsa_entities if e.get("entity_type") == "place"]

    prompt = CONTEXT_SECTIONS_PROMPT.format(
        book_name=state["book_name"],
        genre=state["genre"],
        outline=json.dumps(state.get("structural_outline", {}), indent=2),
        participants=json.dumps(state.get("participant_register", []), indent=2),
        threads=json.dumps(state.get("discourse_threads", []), indent=2),
        bhsa_summary=state.get("bhsa_summary", ""),
        place_entities=json.dumps(place_entities, indent=2),
    )
    if state.get("user_feedback"):
        prompt += (
            "\n\n## User Feedback (address these concerns in your output)\n"
            + state["user_feedback"]
        )
    result = await call_llm(prompt, output_schema=ContextSectionsSchema)
    return {
        "theological_spine": result.theological_spine,
        "places": [p.model_dump() for p in result.places],
        "objects": [o.model_dump() for o in result.objects],
        "institutions": [i.model_dump() for i in result.institutions],
        "genre_context": result.genre_context.model_dump(),
        "maintenance_notes": result.maintenance_notes.model_dump(),
    }
