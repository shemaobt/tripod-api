"""Sound-necklace session tables.

A session is a facilitator's pass over one recorded story. It carries the grid
parameters the SPA needs to reopen the audio, its lifecycle status, and — in a
dedicated narrow table — the state document the SPA autosaves.

The enums live here, not with the DTOs that expose them: the database constrains
each to exactly these values, so a value change has to arrive with a migration.
Portuguese survives only inside the state document, which is the SPA's and is
never interpreted here.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class SessionStatus(enum.StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class SessionStep(enum.StrEnum):
    LISTEN = "listen"
    CUT = "cut"
    TRIAGE = "triage"
    PHRASES = "phrases"
    CONVERSATION = "conversation"
    SAVE = "save"


class GranularityLevel(enum.StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class ArtifactKind(enum.StrEnum):
    """Which of the three artifacts. The stored FILENAMES stay Portuguese
    (``manifesto-contas.json``, ``retorno-ancoragem.json``,
    ``relatorio-mapeamento.md``): PRD §10 freezes them as part of the contract shared
    with the downstream pipeline. The kind is the handle, not the file."""

    MANIFEST = "manifest"
    ANCHORING = "anchoring"
    REPORT = "report"


# `values_callable` makes the database store the value ("in_progress"), not the
# member name ("IN_PROGRESS") — the values are what goes on the wire.
_STATUS_TYPE = Enum(
    SessionStatus,
    name="sn_session_status_enum",
    values_callable=lambda enum_cls: [m.value for m in enum_cls],
)
_ARTIFACT_KIND_TYPE = Enum(
    ArtifactKind,
    name="sn_artifact_kind_enum",
    values_callable=lambda enum_cls: [m.value for m in enum_cls],
)
_STEP_TYPE = Enum(
    SessionStep,
    name="sn_session_step_enum",
    values_callable=lambda enum_cls: [m.value for m in enum_cls],
)
_GRANULARITY_TYPE = Enum(
    GranularityLevel,
    name="sn_granularity_level_enum",
    values_callable=lambda enum_cls: [m.value for m in enum_cls],
)


class SnSession(Base):
    __tablename__ = "sn_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    audio_ref: Mapped[str] = mapped_column(String(255))
    story_name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255))
    manifest_id: Mapped[str] = mapped_column(String(64))
    granularity_level: Mapped[GranularityLevel] = mapped_column(_GRANULARITY_TYPE)
    bead_sec: Mapped[float] = mapped_column(Float)
    pipeline_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[SessionStatus] = mapped_column(_STATUS_TYPE, default=SessionStatus.IN_PROGRESS)
    # The station the saved state was left at. Completion displays as `guardar`
    # without overwriting this, so reopening restores the real station.
    current_step: Mapped[SessionStep] = mapped_column(_STEP_TYPE, default=SessionStep.LISTEN)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SnSessionState(Base):
    """The SPA's autosaved state document, held verbatim.

    ``state`` is TEXT and never JSON: the document is built and re-validated by the
    client under a strict schema, so it is stored as the exact bytes that arrived —
    a JSON column would discard key order and whitespace and the API must never
    re-shape a document it does not own. ``version`` backs the autosave
    compare-and-swap. The row is created with the session and stays empty until the
    first autosave.
    """

    __tablename__ = "sn_session_state"

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sn_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SnArtifact(Base):
    """One of a session's three exported artifacts, held as an opaque object.

    The bytes are NOT here. They live in GCS, exactly as the SPA produced them, and
    this row is the queryable pointer plus the checksums that prove custody. A Postgres
    column would be a trap either way: ``jsonb`` discards key order, whitespace and
    duplicate keys, and even ``text`` invites something downstream to re-encode it. The
    pipeline diffs these files byte for byte against a golden reference (PRD §10.5), so
    the API's only job is to hand back what it was given.

    ``crc32c`` is the checksum GCS itself validated on the way in — a corrupt upload is
    rejected by storage and the object is never created. ``sha256`` is ours, for an
    audit trail that does not depend on trusting the storage provider.

    Keyed by (session, kind): a session has at most one artifact of each kind, and
    re-completing a reopened session replaces it rather than accumulating versions the
    pipeline would then have to choose between.
    """

    __tablename__ = "sn_artifacts"

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sn_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[ArtifactKind] = mapped_column(_ARTIFACT_KIND_TYPE, primary_key=True)
    storage_key: Mapped[str] = mapped_column(String(512))
    size: Mapped[int] = mapped_column(Integer)
    crc32c: Mapped[str] = mapped_column(String(16))
    sha256: Mapped[str] = mapped_column(String(64))
    content_type: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SnVoiceAnswer(Base):
    """One spoken Mapeamento answer, kept by the question it answers.

    Like the artifacts, the bytes are not here — they are a WebM/Opus object in the
    private bucket, and this row is the queryable pointer. The listing is what tells the
    Mapeamento screen which questions already have an answer, which is why the answers
    are a table and not just a bucket prefix: a prefix listing is an extra GCS round trip
    and cannot be joined or scoped in one query.

    ``resource_path`` is the logical, contract-frozen path the SPA builds
    (``respostas/level{1,2,3}/…/<k>.webm``, §10.4) — validated against a fixed allowlist
    before it is ever used, so it can be trusted as the object-name suffix. Keyed by
    (session, path): one file per question (O5), and re-recording replaces in place.
    """

    __tablename__ = "sn_voice_answers"

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sn_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    resource_path: Mapped[str] = mapped_column(String(255), primary_key=True)
    storage_key: Mapped[str] = mapped_column(String(512))
    size: Mapped[int] = mapped_column(Integer)
    content_type: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SnAudioRef(Base):
    """The audios of one project's bucket.

    An acousteme artifact is standalone by design — it carries no project, no
    recording, and its ``audio_id`` is a caller-minted slug rather than a foreign key
    (``oc_acousteme_artifacts``). This row is what gives such an audio a project, and
    that is the whole of its job: without it there is nothing for a project gate to
    stand on, and the audios would only be reachable through the Oral Collector's own
    routes, which have no project scoping at all.

    ``consent_present`` is the collection consent of §12/O6. It is recorded here rather
    than derived: the consent a storyteller gave at recording time lives in
    ``oc_storytellers`` and is reachable only from a recording, which a pilot audio does
    not have. It defaults to False — an unrecorded consent is an absent one, never an
    assumed one.

    One project per audio, mirroring ``oc_recordings``. Sharing one audio across
    projects would widen the key, and nothing asks for that.
    """

    __tablename__ = "sn_audio_refs"

    # Matches oc_acousteme_artifacts.audio_id, which this joins to by convention and
    # not by constraint — the acousteme table is deliberately free of foreign keys.
    audio_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    consent_present: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
