from __future__ import annotations

import logging

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.book_context import BCDGenerationLog, BCDStatus, BookContextDocument
from app.services.book_context.generation.nodes.collect_bhsa import collect_bhsa
from app.services.book_context.generation.nodes.context_sections import generate_context_sections
from app.services.book_context.generation.nodes.discourse import generate_discourse_threads
from app.services.book_context.generation.nodes.participants import generate_participants
from app.services.book_context.generation.nodes.structural_outline import (
    generate_structural_outline,
)
from app.services.book_context.generation.state import BCDGenerationState
from app.services.book_context.get_bcd import get_bcd_or_404
from app.services.book_context.track_step import track_step

logger = logging.getLogger(__name__)

SECTION_FIELDS = (
    "structural_outline",
    "participant_register",
    "discourse_threads",
    "theological_spine",
    "places",
    "objects",
    "institutions",
    "genre_context",
    "maintenance_notes",
)


async def run_bcd_generation(
    db: AsyncSession,
    bcd_id: str,
    book_name: str,
    genre: str,
    chapter_count: int,
    user_feedback: str | None = None,
) -> BookContextDocument:
    bcd = await get_bcd_or_404(db, bcd_id)
    bcd.status = BCDStatus.GENERATING
    if user_feedback:
        bcd.regeneration_feedback = user_feedback
    await db.execute(delete(BCDGenerationLog).where(BCDGenerationLog.bcd_id == bcd_id))
    await db.commit()

    state: BCDGenerationState = {
        "book_name": book_name,
        "book_id": bcd.book_id,
        "bcd_id": bcd_id,
        "genre": genre,
        "chapter_count": chapter_count,
    }
    if user_feedback:
        state["user_feedback"] = user_feedback

    steps = [
        (1, "collect_bhsa", collect_bhsa, False),
        (2, "structural_outline", generate_structural_outline, True),
        (3, "participants", generate_participants, True),
        (4, "discourse", generate_discourse_threads, True),
        (5, "context_sections", generate_context_sections, True),
    ]

    try:
        for order, step_name, node_fn, is_async in steps:
            async with track_step(db, bcd_id, step_name, order, input_summary=step_name) as log:
                if is_async:
                    result = await node_fn(state)
                else:
                    result = node_fn(state)
                state.update(result)
                log.output_summary = f"Completed {step_name}"
    except Exception as exc:
        logger.exception("BCD generation failed at step for %s", bcd_id)
        bcd = await get_bcd_or_404(db, bcd_id)
        bcd.status = BCDStatus.DRAFT
        bcd.generation_metadata = {
            **(bcd.generation_metadata or {}),
            "last_error": str(exc),
        }
        await db.commit()
        raise

    bcd = await get_bcd_or_404(db, bcd_id)
    for field in SECTION_FIELDS:
        if field in state:
            setattr(bcd, field, state[field])

    bcd.status = BCDStatus.DRAFT
    bcd.generation_metadata = {
        **(bcd.generation_metadata or {}),
        "last_error": None,
    }
    await db.commit()
    await db.refresh(bcd)
    return bcd
