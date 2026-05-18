from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.exceptions import ConflictError
from app.db.models.project_health import PHInterviewStatus
from app.models.project_health import CoverageState, MessageOut
from app.services.project_health.agents.orchestrator import orchestrate_turn
from app.services.project_health.get_interview import get_interview_or_404


async def post_message(
    db: AsyncSession, interview_id: str, content: str
) -> tuple[MessageOut, CoverageState]:
    """Append a team turn, run orchestration, persist facilitator reply + state."""
    interview = await get_interview_or_404(db, interview_id)
    if interview.status != PHInterviewStatus.IN_PROGRESS:
        raise ConflictError("Interview is no longer active")

    team_turn = MessageOut(
        role="team",
        content=content,
        timestamp=datetime.now(UTC).isoformat(),
    )
    messages = [*(interview.messages or []), team_turn.model_dump()]

    response, coverage, updated_evidence = await orchestrate_turn(
        messages, interview.evidence or [], interview.language
    )

    facilitator_turn = MessageOut(
        role="facilitator",
        content=response,
        timestamp=datetime.now(UTC).isoformat(),
    )
    messages.append(facilitator_turn.model_dump())

    interview.messages = messages
    interview.coverage_state = coverage.model_dump()
    interview.evidence = updated_evidence
    flag_modified(interview, "messages")
    flag_modified(interview, "coverage_state")
    flag_modified(interview, "evidence")

    await db.commit()
    return facilitator_turn, coverage
