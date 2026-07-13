"""Pydantic DTOs for the Sound Necklace (Colar de Sons) app module — the wire
contract the SPA generates TypeScript from (PRD v2 §5, code-first OpenAPI).

PROVISIONAL: every schema here is a stub surface. The ``/api/colar`` routes
return 501 until each resource issue (sessions ENG-260, audio bucket ENG-261,
voice answers, artifacts, …) lands and replaces them. All models carry
``x-stability: experimental`` in their JSON schema so the SPA treats the
generated types as provisional.

Shapes mirror the SPA's provisional Zod contracts (sound-necklace
``contracts/api.ts`` + ``contracts/bucket.ts``, ENG-235) so both tracks meet at
one contract. §10.5 opaque custody: artifacts and the session-state payload pass
as opaque values — never parsed or re-serialized here.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _ColarModel(BaseModel):
    """Base for every Colar DTO: ORM-friendly and marked provisional."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"x-stability": "experimental"},
    )


# ── Enums ─────────────────────────────────────────────────────────────────────


class SessionStatus(StrEnum):
    em_progresso = "em_progresso"
    concluida = "concluida"


class SessionStep(StrEnum):
    ouvir = "ouvir"
    cortar = "cortar"
    triagem = "triagem"
    frases = "frases"
    conversa = "conversa"
    guardar = "guardar"


class GranularityLevel(StrEnum):
    pequena = "pequena"
    media = "media"
    grande = "grande"


class ArtifactKind(StrEnum):
    manifesto = "manifesto"
    retorno = "retorno"
    relatorio = "relatorio"


# ── Sessions (§7.2/§7.3 — real lifecycle/persistence in ENG-260) ──────────────

MANIFEST_ID_PATTERN = r"^fnv1a32:[0-9a-f]{8}$"


class SessionProgress(_ColarModel):
    current_step: SessionStep


class SessionSummary(_ColarModel):
    id: str
    project_id: str
    story_name: str
    story_slug: str
    status: SessionStatus
    last_modified: str
    progress: SessionProgress


class SessionListResponse(_ColarModel):
    sessions: list[SessionSummary]


class CreateSessionRequest(_ColarModel):
    audio_id: str
    project_id: str
    story_name: str
    story_slug: str
    granularity_level: GranularityLevel
    bead_sec: float = Field(gt=0)
    manifest_id: str = Field(pattern=MANIFEST_ID_PATTERN)
    pipeline_consent: bool


class SessionStatePayload(_ColarModel):
    """Autosave body (§7.3): opaque session-state envelope. Only the version is
    validated; the rest of the state passes through unread (``extra='allow'``)."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="allow",
        json_schema_extra={"x-stability": "experimental"},
    )

    schema_version: int


class AutosaveResponse(_ColarModel):
    saved_at: str
    schema_version: int


# ── Advisory lock (§7.3/O4 — real acquire/renew/release in ENG-260) ───────────


class LockHolder(_ColarModel):
    user_id: str
    display_name: str


class LockStatus(_ColarModel):
    held: bool
    holder: LockHolder | None = None
    expires_at: str | None = None


# ── Artifacts (§8.8/§10.5 — OPAQUE bytes; never parsed or re-serialized) ──────


class ArtifactTriple(_ColarModel):
    manifesto: str
    retorno: str
    relatorio: str


class CompleteSessionRequest(_ColarModel):
    artifacts: ArtifactTriple


# ── Resources: voice answers by canonical ``respostas/...`` path (§10.4) ──────

RESOURCE_PATH_PATTERN = (
    r"^respostas/(level1/[a-z0-9_]+"
    r"|level2/PT[1-9][0-9]*/[a-z0-9_]+"
    r"|level3/P[1-9][0-9]*/[a-z0-9_]+)\.webm$"
)


class ResourceRef(_ColarModel):
    path: str = Field(pattern=RESOURCE_PATH_PATTERN)


class PresignResponse(_ColarModel):
    url: str


# ── Bucket audios (§7.4 — real listing/signing in ENG-261) ────────────────────


class AcoustemeEnvelope(_ColarModel):
    """OPAQUE versioned acousteme envelope (§6.1/§15.2 O8). The API stores/serves
    it and NEVER interprets ``data``. ENG-261 reconciles the concrete shape
    against tripod-api PR #100 (``AcoustemeStreamResponse``)."""

    version: int
    data: dict[str, Any]


class BucketAudio(_ColarModel):
    id: str
    filename: str
    duration_sec: float = Field(gt=0)
    consent_present: bool
    acousteme: AcoustemeEnvelope | None = None


class BucketListResponse(_ColarModel):
    audios: list[BucketAudio]


class AudioUrlResponse(_ColarModel):
    url: str
