from __future__ import annotations

from app.services.book_context.generation.llm import call_llm
from app.services.book_context.generation.schemas import StructuralOutlineSchema
from app.services.book_context.generation.state import BCDGenerationState

STRUCTURAL_OUTLINE_PROMPT = """\
You are a biblical scholar analyzing the structure of {book_name} ({genre}).

BHSA linguistic data summary:
{bhsa_summary}

Think step by step:
1. First, identify the major literary sections of the book based on the clause patterns.
2. For each chapter, identify the main events and narrative movements.
3. Note where the narrative flow changes (indicated by clause type shifts, new names appearing, \
or verb tense changes).
4. Synthesize into a structural outline.

Produce a structural outline with:
- book_arc: A 2-3 sentence summary of the book's overall narrative arc
- chapters: For each chapter, provide a title, summary, and key events
- literary_structure: Describe the literary structure (chiasm, parallel, linear, etc.)
"""


async def generate_structural_outline(state: BCDGenerationState) -> dict:
    prompt = STRUCTURAL_OUTLINE_PROMPT.format(
        book_name=state["book_name"],
        genre=state["genre"],
        bhsa_summary=state.get("bhsa_summary", ""),
    )
    if state.get("user_feedback"):
        prompt += (
            "\n\n## User Feedback (address these concerns in your output)\n"
            + state["user_feedback"]
        )
    result = await call_llm(prompt, output_schema=StructuralOutlineSchema)
    return {"structural_outline": result.model_dump()}
