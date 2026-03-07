from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def generate_bcd_task(
    bcd_id: str,
    book_name: str,
    genre: str,
    chapter_count: int,
) -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.book_context.generation.run import run_bcd_generation

    logger.info("Starting BCD generation for %s (bcd_id=%s)", book_name, bcd_id)

    async with AsyncSessionLocal() as db:
        try:
            bcd = await run_bcd_generation(db, bcd_id, book_name, genre, chapter_count)
            logger.info("BCD generation completed for %s (bcd_id=%s)", book_name, bcd_id)
            return {"bcd_id": bcd.id, "status": bcd.status.value}
        except Exception:
            logger.exception("BCD generation failed for %s (bcd_id=%s)", book_name, bcd_id)
            raise


def register_task() -> None:
    from app.core.task_queue import get_task_app

    app = get_task_app()
    app.task(name="generate_bcd", retry=0, queue="bcd_generation")(generate_bcd_task)
