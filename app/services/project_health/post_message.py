from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.exceptions import ConflictError
from app.db.models.project_health import PHInterviewStatus
from app.models.project_health import CoverageState, MessageOut
from app.services.project_health.agents.orchestrator import orchestrate_turn
from app.services.project_health.get_interview import get_interview_or_404
from app.services.project_health.interview_rules import MAX_TEAM_TURNS_HARD

MAX_TEAM_TURNS_MESSAGES: dict[str, str] = {
    "en": (
        f"This interview has reached its maximum length of {MAX_TEAM_TURNS_HARD} "
        "team turns. Please finish the interview to receive your report."
    ),
    "pt": (
        f"Esta entrevista atingiu o tamanho máximo de {MAX_TEAM_TURNS_HARD} "
        "turnos da equipe. Por favor, finalize a entrevista para receber seu relatório."
    ),
    "es": (
        f"Esta entrevista ha alcanzado su duración máxima de {MAX_TEAM_TURNS_HARD} "
        "turnos del equipo. Por favor, finalice la entrevista para recibir su informe."
    ),
    "fr": (
        f"Cet entretien a atteint sa durée maximale de {MAX_TEAM_TURNS_HARD} "
        "tours d'équipe. Veuillez terminer l'entretien pour recevoir votre rapport."
    ),
    "id": (
        f"Wawancara ini telah mencapai panjang maksimum {MAX_TEAM_TURNS_HARD} "
        "giliran tim. Silakan akhiri wawancara untuk menerima laporan Anda."
    ),
    "sw": (
        f"Mahojiano haya yamefikia urefu wa juu wa zamu {MAX_TEAM_TURNS_HARD} "
        "za timu. Tafadhali maliza mahojiano ili kupokea ripoti yako."
    ),
}


async def post_message(
    db: AsyncSession, interview_id: str, content: str
) -> tuple[MessageOut, CoverageState]:
    """Append a team turn, run orchestration, persist facilitator reply + state.

    Holds a `SELECT ... FOR UPDATE` row lock on the interview for the duration
    of orchestration so concurrent POSTs serialize behind the same row instead
    of stepping on each other's JSON-column writes.
    """
    interview = await get_interview_or_404(db, interview_id, for_update=True)
    if interview.status != PHInterviewStatus.IN_PROGRESS:
        raise ConflictError("Interview is no longer active")

    team_turn_count = sum(1 for m in (interview.messages or []) if m.get("role") == "team")
    if team_turn_count >= MAX_TEAM_TURNS_HARD:
        raise ConflictError(
            MAX_TEAM_TURNS_MESSAGES.get(interview.language.value, MAX_TEAM_TURNS_MESSAGES["en"])
        )

    team_turn = MessageOut(
        role="team",
        content=content,
        timestamp=datetime.now(UTC).isoformat(),
    )
    messages = [*(interview.messages or []), team_turn.model_dump()]

    response, coverage, updated_evidence = await orchestrate_turn(
        db, messages, interview.evidence or [], interview.language
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
