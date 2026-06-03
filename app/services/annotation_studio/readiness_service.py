from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.as_enums import AsSortDimension as SortDimension
from app.core.as_enums import AsSortRound as SortRound
from app.core.as_enums import AsUploadStatus as UploadStatus
from app.db.models.as_tier_a import AsTierARecording, AsTierAWord
from app.db.models.as_tier_b import AsTierBPair, AsTierBRecording
from app.db.models.as_tier_c import AsTierCClip, AsTierCSortAssignment
from app.services.annotation_studio.export_plan import MIN_INSTANCES_PER_WORD


async def compute_readiness(db: AsyncSession, language_id: str) -> dict:
    words = (
        (await db.execute(select(AsTierAWord.id).where(AsTierAWord.language_id == language_id)))
        .scalars()
        .all()
    )
    a_recs = await db.execute(
        select(AsTierARecording.word_id)
        .join(AsTierAWord, AsTierARecording.word_id == AsTierAWord.id)
        .where(
            AsTierAWord.language_id == language_id,
            AsTierARecording.upload_status == UploadStatus.STORED.value,
        )
    )
    per_word = Counter(row[0] for row in a_recs.all())
    words_ready = sum(1 for count in per_word.values() if count >= MIN_INSTANCES_PER_WORD)

    pairs = (
        (await db.execute(select(AsTierBPair.id).where(AsTierBPair.language_id == language_id)))
        .scalars()
        .all()
    )
    b_recs = (
        await db.execute(
            select(AsTierBRecording.id)
            .join(AsTierBPair, AsTierBRecording.pair_id == AsTierBPair.id)
            .where(
                AsTierBPair.language_id == language_id,
                AsTierBRecording.upload_status == UploadStatus.STORED.value,
            )
        )
    ).all()

    clips = (
        await db.execute(
            select(AsTierCClip.id).where(
                AsTierCClip.language_id == language_id,
                AsTierCClip.upload_status == UploadStatus.STORED.value,
            )
        )
    ).all()

    sorted_rows = await db.execute(
        select(AsTierCSortAssignment.dimension, AsTierCSortAssignment.clip_id)
        .join(AsTierCClip, AsTierCSortAssignment.clip_id == AsTierCClip.id)
        .where(
            AsTierCClip.language_id == language_id,
            AsTierCSortAssignment.round == SortRound.NORMAL.value,
            AsTierCSortAssignment.group_label.is_not(None),
        )
    )
    onset_sorted = 0
    coda_sorted = 0
    for dimension, _clip_id in sorted_rows.all():
        if dimension == SortDimension.ONSET.value:
            onset_sorted += 1
        else:
            coda_sorted += 1

    return {
        "tier_a": {
            "words_total": len(words),
            "words_ready": words_ready,
            "instances": sum(per_word.values()),
            "min_instances": MIN_INSTANCES_PER_WORD,
        },
        "tier_b": {"pairs": len(pairs), "recordings": len(b_recs)},
        "tier_c": {
            "clips": len(clips),
            "onset_sorted": onset_sorted,
            "coda_sorted": coda_sorted,
        },
    }
