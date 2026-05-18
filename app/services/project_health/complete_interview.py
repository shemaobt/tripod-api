from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ValidationError
from app.db.models.project_health import PHInterviewStatus, PHReport
from app.models.project_health import (
    InterviewCompleteBlockedResponse,
    TeamReport,
)
from app.services.project_health.agents.orchestrator import generate_reports
from app.services.project_health.get_interview import get_interview_or_404
from app.services.project_health.interview_rules import (
    MIN_TEAM_TURNS,
    can_complete_interview,
    get_missing_domains,
    get_missing_opening_fields,
    normalize_coverage_state,
)


class InterviewIncompleteError(ValidationError):
    def __init__(self, payload: InterviewCompleteBlockedResponse) -> None:
        super().__init__(payload.error)
        self.payload = payload


BLOCKED_MESSAGES = {
    "en": (
        "Please continue a little longer so we can hear a fuller picture of the "
        "project before preparing the report."
    ),
    "pt": (
        "Continue um pouco mais para que possamos ouvir um quadro mais completo "
        "do projeto antes de preparar o relatório."
    ),
    "es": (
        "Continúen un poco más para que podamos escuchar un panorama más completo "
        "del proyecto antes de preparar el informe."
    ),
    "fr": (
        "Continuez encore un peu afin que nous puissions entendre un tableau plus "
        "complet du projet avant de préparer le rapport."
    ),
    "id": (
        "Lanjutkan sedikit lagi supaya kami bisa memahami gambaran proyek dengan "
        "lebih lengkap sebelum menyiapkan laporan."
    ),
    "sw": (
        "Tafadhali endeleeni kidogo zaidi ili tupate picha kamili ya mradi kabla "
        "ya kuandaa ripoti."
    ),
}


async def complete_interview(
    db: AsyncSession, interview_id: str
) -> tuple[str, TeamReport]:
    """Generate team + admin reports and persist them. Idempotent: returns the
    existing report if one was previously generated for this interview."""
    interview = await get_interview_or_404(db, interview_id)
    if interview.status == PHInterviewStatus.COMPLETED:
        existing = await _fetch_existing_report(db, interview_id)
        if existing:
            team_report = TeamReport.model_validate(existing.team_report)
            return existing.id, team_report
        raise ConflictError("Interview is completed but no report exists")
    if interview.status != PHInterviewStatus.IN_PROGRESS:
        raise ConflictError("Interview is no longer active")

    existing = await _fetch_existing_report(db, interview_id)
    if existing:
        team_report = TeamReport.model_validate(existing.team_report)
        return existing.id, team_report

    coverage = normalize_coverage_state(interview.coverage_state)
    team_turn_count = sum(
        1 for m in (interview.messages or []) if m.get("role") == "team"
    )
    if not can_complete_interview(coverage, team_turn_count):
        blocked = InterviewCompleteBlockedResponse(
            error=BLOCKED_MESSAGES.get(
                interview.language.value, BLOCKED_MESSAGES["en"]
            ),
            completion_ready=False,
            minimum_team_turns=MIN_TEAM_TURNS,
            team_turn_count=team_turn_count,
            missing_opening_fields=get_missing_opening_fields(coverage),
            missing_domains=get_missing_domains(coverage),
        )
        raise InterviewIncompleteError(blocked)

    team_report, admin_report = await generate_reports(
        messages=interview.messages or [],
        evidence=interview.evidence or [],
        language=interview.language,
        coverage=coverage,
    )

    report = PHReport(
        interview_id=interview.id,
        team_report=team_report.model_dump(),
        admin_report=admin_report.model_dump(),
    )
    db.add(report)
    interview.status = PHInterviewStatus.COMPLETED
    interview.completed_at = datetime.now(UTC)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await _fetch_existing_report(db, interview.id)
        if existing is None:
            raise
        return existing.id, TeamReport.model_validate(existing.team_report)
    await db.refresh(report)
    return report.id, team_report


async def _fetch_existing_report(
    db: AsyncSession, interview_id: str
) -> PHReport | None:
    stmt = select(PHReport).where(PHReport.interview_id == interview_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
