import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.book_context import BCDGenerationLog


@asynccontextmanager
async def track_step(
    db: AsyncSession,
    bcd_id: str,
    step_name: str,
    step_order: int,
    *,
    input_summary: str | None = None,
) -> AsyncIterator[BCDGenerationLog]:
    log = BCDGenerationLog(
        bcd_id=bcd_id,
        step_name=step_name,
        step_order=step_order,
        status="running",
        started_at=datetime.now(UTC),
        input_summary=input_summary,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    start = time.monotonic()
    try:
        yield log
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        log.status = "failed"
        log.completed_at = datetime.now(UTC)
        log.duration_ms = elapsed_ms
        log.error_detail = str(exc)
        await db.commit()
        raise
    else:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        log.status = "completed"
        log.completed_at = datetime.now(UTC)
        log.duration_ms = elapsed_ms
        await db.commit()
