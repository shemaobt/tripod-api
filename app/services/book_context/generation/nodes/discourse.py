from __future__ import annotations

import json

from app.services.book_context.generation.llm import call_llm
from app.services.book_context.generation.schemas import DiscourseThreadsSchema
from app.services.book_context.generation.state import BCDGenerationState

DISCOURSE_PROMPT = """\
You are a biblical scholar identifying discourse threads in {book_name}.

Structural outline:
{outline}

Participant register:
{participants}

BHSA linguistic data summary:
{bhsa_summary}

Think step by step:
1. Identify the key tensions, questions, and unresolved issues that drive the narrative.
2. For each thread, find where it opens (first verse where the tension appears).
3. Track how the thread develops across episodes — what is the status at each key point?
4. Determine if and where each thread is resolved.

A discourse thread represents a narrative tension the audience is tracking. Examples:
- "Will Naomi find security?" (opened at Ruth 1:1, resolved at 4:17)
- "Who will redeem?" (opened at 2:20, resolved at 4:10)

For each thread, provide:
- label: Short descriptive label
- opened_at: {{chapter, verse}} where the tension first appears
- resolved_at: {{chapter, verse}} where it resolves (null if unresolved)
- question: The question the audience is holding
- status_by_episode: List of {{at: {{chapter, verse}}, status: "description"}} updates
"""


async def generate_discourse_threads(state: BCDGenerationState) -> dict:
    prompt = DISCOURSE_PROMPT.format(
        book_name=state["book_name"],
        outline=json.dumps(state.get("structural_outline", {}), indent=2),
        participants=json.dumps(state.get("participant_register", []), indent=2),
        bhsa_summary=state.get("bhsa_summary", ""),
    )
    if state.get("user_feedback"):
        prompt += (
            "\n\n## User Feedback (address these concerns in your output)\n"
            + state["user_feedback"]
        )
    result = await call_llm(prompt, output_schema=DiscourseThreadsSchema)
    return {"discourse_threads": [t.model_dump() for t in result.threads]}
