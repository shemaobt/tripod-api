"""Transcription + translation drafts for a session's voice answers (ENG-325).

One async pass per answer: transcribe in the language it was spoken, then, if that is not
English, translate. Both are drafts for a human to confirm — this module never touches an
artifact.

It runs when the SPA enters the Report, not on upload: a take that gets re-recorded before
the report is never paid for. The per-answer rows carry the whole state of the job, which
is what makes it idempotent (``ready`` is never redone), resumable (a lost worker leaves
``pending``) and partial-failure-proof (a bad answer is one ``failed`` row, never a 500).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import inngest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SnTranscriptionEvent
from app.core.inngest_client import inngest_client
from app.db.models.sound_necklace import SnAnswerTranscript, SnVoiceAnswer, TranscriptStatus
from app.services.oral_collector import gcs_utils
from app.services.platform.stt import SpeechToText, transcribe_speech
from app.services.platform.translation import Translator, translate_to_english
from app.services.platform.voices import language_hint
from app.services.sound_necklace.constants import GCS_SN_BUCKET

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TranscriptionProgress:
    """What the polling endpoint answers with — counts plus the per-answer detail."""

    total: int
    ready: int
    failed: int
    pending: int
    answers: list[SnAnswerTranscript]


async def start_transcription(
    db: AsyncSession, session_id: str, *, language: str, force: bool = False
) -> TranscriptionProgress:
    """Queue the drafts that are missing, and return the progress right away.

    A ``ready`` draft is left alone — that is the idempotency, and it is what keeps a
    reloaded report from re-billing every answer. A ``failed`` one is queued again without
    ``force``: retrying a provider outage is the expected path, not an override.

    ``force`` is the re-record case: it throws the existing drafts away, because a draft
    of a take that no longer exists is worse than no draft at all.
    """
    answers = (
        (
            await db.execute(
                select(SnVoiceAnswer)
                .where(SnVoiceAnswer.session_id == session_id)
                .order_by(SnVoiceAnswer.resource_path)
            )
        )
        .scalars()
        .all()
    )

    # Both sides in two queries, not one per answer: a session carries a draft for every
    # question of every scene and phrase, so a lookup per answer is that many round trips
    # on the one request the report is waiting for.
    existing = {
        draft.resource_path: draft
        for draft in (
            await db.execute(
                select(SnAnswerTranscript).where(SnAnswerTranscript.session_id == session_id)
            )
        ).scalars()
    }

    for answer in answers:
        draft = existing.get(answer.resource_path)
        if draft is None:
            draft = SnAnswerTranscript(
                session_id=session_id, resource_path=answer.resource_path, language=language
            )
            db.add(draft)
        elif draft.status == TranscriptStatus.READY and not force:
            continue

        draft.language = language
        draft.status = TranscriptStatus.PENDING
        draft.transcript_source = None
        draft.translation_en = None
        draft.error = None

    await db.commit()
    return await transcription_progress(db, session_id)


async def transcription_progress(db: AsyncSession, session_id: str) -> TranscriptionProgress:
    """The state of every answer's draft, counted.

    ``total`` counts the DRAFTS, not the recordings: an answer recorded after the trigger
    has no draft yet and is not work this job was asked to do.
    """
    drafts = (
        (
            await db.execute(
                select(SnAnswerTranscript)
                .where(SnAnswerTranscript.session_id == session_id)
                .order_by(SnAnswerTranscript.resource_path)
            )
        )
        .scalars()
        .all()
    )
    by_status = [d.status for d in drafts]
    return TranscriptionProgress(
        total=len(drafts),
        ready=by_status.count(TranscriptStatus.READY),
        failed=by_status.count(TranscriptStatus.FAILED),
        pending=by_status.count(TranscriptStatus.PENDING),
        answers=list(drafts),
    )


async def run_pending(
    db: AsyncSession,
    session_id: str,
    *,
    stt: SpeechToText = transcribe_speech,
    translator: Translator = translate_to_english,
) -> None:
    """Fill in every pending draft of the session, one answer at a time.

    Sequential on purpose: one session, one row committed per answer, so progress is
    visible while it runs and a crash costs at most the answer in flight.

    ponytail: a 200-answer session takes 200 round trips end to end. If that becomes the
    complaint, fan out with one DB session per worker — not with a shared one, which is
    not concurrency-safe.
    """
    pending = (
        (
            await db.execute(
                select(SnAnswerTranscript, SnVoiceAnswer)
                .join(
                    SnVoiceAnswer,
                    (SnVoiceAnswer.session_id == SnAnswerTranscript.session_id)
                    & (SnVoiceAnswer.resource_path == SnAnswerTranscript.resource_path),
                )
                .where(
                    SnAnswerTranscript.session_id == session_id,
                    SnAnswerTranscript.status == TranscriptStatus.PENDING,
                )
                .order_by(SnAnswerTranscript.resource_path)
            )
        )
        .tuples()
        .all()
    )

    for draft, answer in pending:
        try:
            audio = await gcs_utils.download_gcs_object(GCS_SN_BUCKET, answer.storage_key)
            transcript = await stt(audio, language=draft.language, mime_type=answer.content_type)
            draft.transcript_source = transcript
            # An English interview is already the English text the report wants. The branch
            # is here, not only inside the translator, because "transcribe, then translate
            # if it is not English" is the job's rule — and a call not made is a call not
            # billed, whichever provider is configured.
            draft.translation_en = (
                transcript
                if language_hint(draft.language) == "en"
                else await translator(transcript, source_language=draft.language)
            )
            draft.status = TranscriptStatus.READY
            draft.error = None
        except Exception as exc:
            # A failure is this answer's state, never the job's and never a 500. The
            # message is what a facilitator sees next to a red answer, so it is the
            # provider's own words rather than a generic one.
            logger.warning(
                "transcription failed session=%s path=%s: %s",
                session_id,
                draft.resource_path,
                exc,
            )
            draft.status = TranscriptStatus.FAILED
            draft.error = str(exc)
        await db.commit()


async def request_transcription(session_id: str) -> None:
    """Hand the pass to the queue — the request does not wait for it or run it.

    The event carries the session and nothing else: the run reads whatever is `pending`
    when it starts, so a retry or a replay costs no provider call it has already made.
    """
    # Imported here, not at module scope: `app.inngest` registers the function that imports
    # this module, so a top-level import would close the loop. The queue is the outer layer
    # and knows the service; the service only needs the payload's shape, and only when it
    # sends.
    from app.inngest.schemas import TranscriptionRequestedPayload

    await inngest_client.send(
        inngest.Event(
            name=SnTranscriptionEvent.REQUESTED,
            data=TranscriptionRequestedPayload(session_id=session_id).model_dump(),
        )
    )
