"""Pydantic schemas for the sound-necklace app module.

The wire contract the SPA generates its TypeScript types from (code-first
OpenAPI). Provisional: the resources not yet implemented are stubs returning 501, so
every schema is tagged ``x-stability: experimental`` and mirrors the SPA's provisional
contracts (sound-necklace ``contracts/``). Artifacts and the session-state envelope are
opaque — never parsed or re-serialized here.

Where this and the SPA's provisional contracts disagree, this wins and the SPA
regenerates: its ``contracts/bucket.ts`` still types the codebook version as an integer
and the audio duration as non-null, and both are wrong against the pipeline that
actually mints them (ENG-261).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.sound_necklace import (
    ArtifactKind,
    GranularityLevel,
    SessionStatus,
    SessionStep,
)

# Vendor extension marking every schema in this module as provisional.
_EXPERIMENTAL: dict[str, Any] = {"x-stability": "experimental"}


# ── Enums ───────────────────────────────────────────────────────────────────
#
# Every enum here is imported from the db model rather than defined here: they all
# back real columns, and the database constrains each to exactly these values. Keeping
# them with the table is what forces a value change to come with a migration.


# ── Artifacts ───────────────────────────────────────────────────────────────
#
# Bytes are uploaded raw (multipart) and served back verbatim from storage: they
# never enter a Pydantic model, so nothing can re-shape them. Only this envelope
# is typed.


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    kind: ArtifactKind
    size: int
    # Both checksums the API recorded, so a consumer can verify a fetched artifact
    # against what was stored rather than trusting the transfer. crc32c is what GCS
    # validates on the way in; sha256 is ours, provider-independent.
    crc32c: str
    sha256: str


# ── Sessions ────────────────────────────────────────────────────────────────

MANIFEST_ID_PATTERN = r"^fnv1a32:[0-9a-f]{8}$"


class SessionProgress(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    current_step: SessionStep


class SessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    id: str
    project_id: str
    story_name: str
    story_slug: str
    status: SessionStatus
    last_modified: str
    progress: SessionProgress


class SessionListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    sessions: list[SessionSummary]


class SessionCreate(BaseModel):
    model_config = ConfigDict(json_schema_extra=_EXPERIMENTAL)

    # The text lengths mirror their columns: unbounded here, an over-long value would
    # reach Postgres and fail the insert instead of failing validation.
    audio_id: str = Field(max_length=255)
    project_id: str
    story_name: str = Field(max_length=255)
    story_slug: str = Field(max_length=255)
    granularity_level: GranularityLevel
    bead_sec: float = Field(gt=0)
    manifest_id: str = Field(pattern=MANIFEST_ID_PATTERN)
    pipeline_consent: bool


class SessionStateUpdate(BaseModel):
    """Autosave body: opaque session-state envelope; only the version is read."""

    model_config = ConfigDict(extra="allow", json_schema_extra=_EXPERIMENTAL)

    schema_version: int


class AutosaveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    saved_at: str
    schema_version: int


# ── Advisory single-editor lock ──────────────────────────────────────────────


class LockHolder(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    user_id: str
    display_name: str


class LockStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    held: bool
    holder: LockHolder | None = None
    expires_at: str | None = None


# ── Voice-answer resources (canonical respostas/... path) ────────────────────

# The logical, contract-frozen path the SPA builds for each answer (§10.4). It is an
# allowlist, not a hint: the three shapes are all that can name an object, which is what
# lets the path be trusted as an object-name suffix — no traversal, no free-form key.
RESOURCE_PATH_PATTERN = (
    r"^respostas/(level1/[a-z0-9_]+"
    r"|level2/PT[1-9][0-9]*/[a-z0-9_]+"
    r"|level3/P[1-9][0-9]*/[a-z0-9_]+)\.webm$"
)


class ResourceSummary(BaseModel):
    """One recorded answer in the listing — the path is what the Mapeamento screen keys
    on to know which questions are answered."""

    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    path: str
    size: int


class ResourceListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    resources: list[ResourceSummary]


class ResourceUrlResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    url: str


# ── Bucket audios ─────────────────────────────────────────────────────────────


class AcoustemeEnvelope(BaseModel):
    """The granularity grid an audio's bead duration is derived from.

    ``beadSec = granularity_frames[level] x hop_sec`` — the two fields exist together
    or the envelope is useless, so an audio whose grid is incomplete carries no
    envelope at all rather than half of one.

    ``codebook_version`` is a string, not a number: it is half of the acousteme
    artifact's primary key and reads like ``terena-xlsr53-k100-v1``. An integer here
    would be a version the pipeline never mints.
    """

    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    codebook_version: str
    hop_sec: float
    granularity_frames: dict[str, int]


class BucketAudioResponse(BaseModel):
    """An audio the facilitator can pick from the project's bucket.

    ``acousteme`` is null when no servable grid exists for the audio — an ingest that
    never succeeded, or an audio that was never tokenized. That is a fallback, not an
    error (PRD §6.1: the levels then map to fixed durations), so the audio still lists.

    ``duration_sec`` is nullable because response models are validated on the way
    out: one un-probed audio would otherwise fail validation of the whole listing.
    The invariant belongs at ingestion, where a violation is actionable.
    """

    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    id: str
    filename: str
    duration_sec: float | None = None
    consent_present: bool
    acousteme: AcoustemeEnvelope | None = None


class BucketAudioListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    audios: list[BucketAudioResponse]


class AudioUrlResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    url: str
