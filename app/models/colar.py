"""Pydantic schemas for the Sound Necklace (Colar de Sons) app module.

The wire contract the SPA generates its TypeScript types from (code-first
OpenAPI). Provisional: the ``/api/colar`` routes are stubs returning 501 until
each resource is implemented, so every schema is tagged ``x-stability: experimental``
and mirrors the SPA's provisional contracts (sound-necklace ``contracts/``).
Artifacts and the session-state envelope are opaque — never parsed or
re-serialized here.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Vendor extension marking every schema in this module as provisional.
_EXPERIMENTAL: dict[str, Any] = {"x-stability": "experimental"}


# ── Enums (identifiers English; values are the SPA wire contract) ───────────


class SessionStatus(StrEnum):
    IN_PROGRESS = "em_progresso"
    COMPLETED = "concluida"


class SessionStep(StrEnum):
    LISTEN = "ouvir"
    CUT = "cortar"
    TRIAGE = "triagem"
    PHRASES = "frases"
    CONVERSATION = "conversa"
    SAVE = "guardar"


class GranularityLevel(StrEnum):
    SMALL = "pequena"
    MEDIUM = "media"
    LARGE = "grande"


class ArtifactKind(StrEnum):
    MANIFESTO = "manifesto"
    RETORNO = "retorno"
    RELATORIO = "relatorio"


# ── Artifacts (opaque bytes; never parsed or re-serialized) ─────────────────


class ArtifactTriple(BaseModel):
    model_config = ConfigDict(json_schema_extra=_EXPERIMENTAL)

    manifesto: str
    retorno: str
    relatorio: str


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

    audio_id: str
    project_id: str
    story_name: str
    story_slug: str
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


class SessionCompleteRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra=_EXPERIMENTAL)

    artifacts: ArtifactTriple


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

RESOURCE_PATH_PATTERN = (
    r"^respostas/(level1/[a-z0-9_]+"
    r"|level2/PT[1-9][0-9]*/[a-z0-9_]+"
    r"|level3/P[1-9][0-9]*/[a-z0-9_]+)\.webm$"
)


class ResourceRef(BaseModel):
    model_config = ConfigDict(json_schema_extra=_EXPERIMENTAL)

    path: str = Field(pattern=RESOURCE_PATH_PATTERN)


class ResourcePresignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    url: str


# ── Bucket audios ─────────────────────────────────────────────────────────────


class AcoustemeEnvelope(BaseModel):
    """Opaque versioned acousteme envelope; the API never interprets ``data``."""

    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    version: int
    data: dict[str, Any]


class BucketAudioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    id: str
    filename: str
    duration_sec: float = Field(gt=0)
    consent_present: bool
    acousteme: AcoustemeEnvelope | None = None


class BucketAudioListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    audios: list[BucketAudioResponse]


class AudioUrlResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra=_EXPERIMENTAL)

    url: str
