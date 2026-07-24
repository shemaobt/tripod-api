from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ProjectGranularityLocked
from app.db.models.sound_necklace import (
    GranularityLevel,
    SnProjectSettings,
    SnSession,
)


async def _has_sessions(db: AsyncSession, project_id: str) -> bool:
    """Whether anything has been cut on this project yet.

    Counted rather than joined off the settings row: a session created before this table
    existed has no row to point at, and those are exactly the projects whose granularity
    must already be frozen.
    """
    count = await db.scalar(
        select(func.count()).select_from(SnSession).where(SnSession.project_id == project_id)
    )
    return bool(count)


async def get_project_settings(
    db: AsyncSession, project_id: str
) -> tuple[SnProjectSettings | None, bool]:
    """The project's granularity row (or None) and whether the level is frozen."""
    row = await db.get(SnProjectSettings, project_id)
    return row, await _has_sessions(db, project_id)


async def set_project_granularity(
    db: AsyncSession, project_id: str, level: GranularityLevel, updated_by: str
) -> tuple[SnProjectSettings, bool]:
    """Decide the project's bead granularity, while it is still decidable.

    Refused once the project has a session. That is the rule the whole setting rests on:
    moving the level afterwards would either contradict the ``bead_sec`` already stamped
    — leaving the project unable to open another session, since every new audio would
    resolve to a grid the stored one rejects — or split the corpus across two coordinate
    systems, which is the thing this row exists to prevent.

    Re-sending the level a project already has is not a change and is allowed through: a
    settings screen may save what is already on it, and refusing that would make the
    frozen state impossible to render honestly.
    """
    locked = await _has_sessions(db, project_id)
    row = await db.get(SnProjectSettings, project_id)

    if row is not None and row.granularity_level == level:
        return row, locked
    if locked:
        raise ProjectGranularityLocked(
            "This project has already been cut at its bead granularity, so the level "
            "cannot change. Re-cutting it means re-deriving every manifest_id already "
            "exported."
        )

    if row is None:
        row = SnProjectSettings(project_id=project_id)
        db.add(row)
    row.granularity_level = level
    row.updated_by = updated_by

    await db.commit()
    await db.refresh(row)
    return row, locked


async def stamp_resolved_bead_sec(
    db: AsyncSession, project_id: str, level: GranularityLevel, bead_sec: float
) -> None:
    """Record the grid the project's first session landed on.

    ``bead_sec`` is ``granularity_frames[level] * hop_sec`` off the audio's own acousteme,
    so nothing knows it before an audio is cut — the admin picks a level, the first
    session resolves it. From then on it is the value later audios have to agree with,
    and the SPA refuses one whose acousteme would resolve differently.

    Writes the level too when no row exists. Sessions predate this table, and a project
    grandfathered in that way still needs its grid written down; the level it was cut at
    IS the project's level. It never overwrites a level already decided — a session that
    somehow disagreed with its project would be a bug to surface, not to enshrine.

    Called inside ``create_session``'s transaction and does not commit: that call site
    owns the commit that lands the session, its state row and its consent together.
    """
    row = await db.get(SnProjectSettings, project_id)
    if row is None:
        row = SnProjectSettings(project_id=project_id, granularity_level=level)
        db.add(row)
    if row.bead_sec is None:
        row.bead_sec = bead_sec
