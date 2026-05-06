import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.models.book_context import BookContextDocument
from app.models.book_context import ParticipantType

logger = logging.getLogger(__name__)


_VALID_TYPES: frozenset[str] = frozenset(t.value for t in ParticipantType)


def _normalize_participant(participant: dict, bcd_id: str) -> bool:
    raw_type = participant.get("type")
    if raw_type in _VALID_TYPES:
        return False

    logger.warning(
        "Mapping legacy participant type %r to 'named' on BCD %s (participant name=%r)",
        raw_type,
        bcd_id,
        participant.get("name"),
    )
    participant["type"] = ParticipantType.NAMED.value
    return True


async def backfill_participant_enums(
    db: AsyncSession, *, dry_run: bool = False
) -> tuple[int, int]:
    stmt = select(BookContextDocument).where(
        BookContextDocument.participant_register.is_not(None)
    )
    result = await db.execute(stmt)
    docs = list(result.scalars().all())

    rows_updated = 0
    docs_visited = 0

    for doc in docs:
        register = doc.participant_register
        if not isinstance(register, list):
            continue

        docs_visited += 1
        doc_changed = False

        for participant in register:
            if not isinstance(participant, dict):
                continue
            if _normalize_participant(participant, doc.id):
                rows_updated += 1
                doc_changed = True

        if doc_changed and not dry_run:
            doc.participant_register = register
            flag_modified(doc, "participant_register")

    if not dry_run:
        await db.commit()

    return rows_updated, docs_visited
