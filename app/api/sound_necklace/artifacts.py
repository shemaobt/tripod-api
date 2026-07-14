"""Artifact stub routes.

The three artifacts are produced client-side and must survive byte-identical, so
they travel as raw multipart bytes on upload and are served straight from storage
on download — no Pydantic model ever parses a payload.
"""

from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import RedirectResponse

from app.api.sound_necklace._deps import CurrentUser, not_implemented
from app.models.sound_necklace import ArtifactKind, ArtifactResponse

router = APIRouter()


@router.post(
    "/sessions/{session_id}/artifacts",
    response_model=list[ArtifactResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_artifacts(
    session_id: str,
    user: CurrentUser,
    manifest: UploadFile = File(),
    anchoring: UploadFile = File(),
    report: UploadFile = File(),
) -> list[ArtifactResponse]:
    """Store the three artifacts as opaque bytes, checksummed on the way in."""
    not_implemented()


@router.get(
    "/sessions/{session_id}/artifacts/{kind}",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    response_class=RedirectResponse,
    response_model=None,
)
async def download_artifact(
    session_id: str, kind: ArtifactKind, user: CurrentUser
) -> RedirectResponse:
    """Redirect to a short-lived signed URL: storage serves the bytes verbatim.

    The API never proxies an artifact's bytes — that is what keeps the download
    byte-identical to the upload.
    """
    not_implemented()
