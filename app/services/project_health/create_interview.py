from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project_health import PHInterview, PHInterviewStatus, PHLanguage
from app.models.project_health import CoverageState, MessageOut
from app.services.project_health.interview_rules import create_initial_coverage_state
from app.services.project_health.interview_token import encode_interview_token

OPENING_MESSAGES: dict[PHLanguage, str] = {
    PHLanguage.EN: (
        "Thank you for being here. Before we begin, please tell me the full "
        "name of the main person answering this interview."
    ),
    PHLanguage.PT: (
        "Obrigado por estarem aqui. Antes de começarmos, por favor me diga o "
        "nome completo da pessoa principal que está respondendo esta entrevista."
    ),
    PHLanguage.ES: (
        "Gracias por estar aquí. Antes de comenzar, por favor dígame el nombre "
        "completo de la persona principal que responderá esta entrevista."
    ),
    PHLanguage.FR: (
        "Merci d'être ici. Avant de commencer, veuillez me dire le nom complet "
        "de la personne principale qui répondra à cet entretien."
    ),
    PHLanguage.ID: (
        "Terima kasih sudah hadir. Sebelum kita mulai, tolong sebutkan nama "
        "lengkap orang utama yang menjawab wawancara ini."
    ),
    PHLanguage.SW: (
        "Asanteni kwa kuwa hapa. Kabla hatujaanza, tafadhali taja jina kamili "
        "la mtu mkuu anayejibu mahojiano haya."
    ),
}


async def create_interview(
    db: AsyncSession,
    *,
    project_name: str,
    team_name: str,
    language: PHLanguage,
) -> tuple[PHInterview, str, datetime, MessageOut, CoverageState]:
    """Create a new project-health interview row, mint an interview-scoped token,
    and seed the first facilitator message in the requested language."""
    coverage = create_initial_coverage_state()
    first_message = MessageOut(
        role="facilitator",
        content=OPENING_MESSAGES[language],
        timestamp=datetime.now(UTC).isoformat(),
    )

    interview = PHInterview(
        project_name=project_name,
        team_name=team_name,
        language=language,
        status=PHInterviewStatus.IN_PROGRESS,
        messages=[first_message.model_dump()],
        coverage_state=coverage.model_dump(),
        evidence=[],
    )
    db.add(interview)
    await db.commit()
    await db.refresh(interview)

    token, expires_at = encode_interview_token(interview.id)
    return interview, token, expires_at, first_message, coverage
