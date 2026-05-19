"""Force-complete stalled Project Health interviews and generate their reports.

Targets interviews stuck in IN_PROGRESS whose team turn count is at least
MIN_TEAM_TURNS and whose opening fields are complete. Idempotent: completed
interviews and ones that already have a report row are skipped.

Run inside the backend container:
    uv run python scripts/backfill_ph_reports.py
"""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.db.models.project_health import PHInterview, PHInterviewStatus
from app.services.project_health.complete_interview import (
    InterviewIncompleteError,
    complete_interview,
)
from app.services.project_health.interview_rules import (
    MIN_TEAM_TURNS,
    can_force_complete_interview,
    normalize_coverage_state,
)


async def main() -> None:
    cutoff = datetime.now(UTC) - timedelta(hours=1)
    completed = 0
    skipped = 0
    failed = 0
    async with AsyncSessionLocal() as db:
        stmt = select(PHInterview).where(
            PHInterview.status == PHInterviewStatus.IN_PROGRESS,
            PHInterview.created_at < cutoff,
        )
        rows = (await db.execute(stmt)).scalars().all()
        for interview in rows:
            team_turns = sum(1 for m in (interview.messages or []) if m.get("role") == "team")
            coverage = normalize_coverage_state(interview.coverage_state)
            if not can_force_complete_interview(coverage, team_turns):
                print(
                    f"skip {interview.id}: team_turns={team_turns} (need >= {MIN_TEAM_TURNS}) "
                    f"or missing opening fields"
                )
                skipped += 1
                continue
            try:
                report_id, _ = await complete_interview(db, interview.id, force=True)
                print(f"completed {interview.id} -> report {report_id}")
                completed += 1
            except InterviewIncompleteError as exc:
                print(f"blocked {interview.id}: {exc.payload.error}")
                skipped += 1
            except Exception as exc:
                print(f"failed {interview.id}: {exc!r}")
                failed += 1
    print(f"Done. completed={completed} skipped={skipped} failed={failed}")


if __name__ == "__main__":
    asyncio.run(main())
