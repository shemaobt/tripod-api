"""Artifact download stub (§8.8/§10.5). Upload happens on session complete.

Artifacts are OPAQUE bytes served exactly as uploaded — never parsed. Implemented
by the artifacts resource issue.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.colar._deps import CurrentUser, not_implemented
from app.models.colar import ArtifactKind

router = APIRouter()


@router.get("/sessions/{session_id}/artifacts/{kind}")
async def download_artifact(session_id: str, kind: ArtifactKind, user: CurrentUser) -> None:
    """Download one opaque artifact (manifesto/retorno/relatorio) by kind (§10.5)."""
    not_implemented()
