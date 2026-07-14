from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.sound_necklace import ArtifactKind, SnArtifact
from app.services.oral_collector import gcs_utils
from app.services.sound_necklace.constants import DOWNLOAD_URL_EXPIRY_MINUTES, GCS_SN_BUCKET


async def artifact_download_url(db: AsyncSession, session_id: str, kind: ArtifactKind) -> str:
    """A short-lived signed GET for one artifact.

    Storage serves the bytes; the API never proxies them — which is exactly what keeps
    the download byte-identical to the upload. A proxy would have to choose an encoding,
    and any choice is a chance to be wrong.

    This is the audit point for an artifact (ENG-266 hooks here).
    """
    artifact = await db.get(SnArtifact, (session_id, kind))
    if artifact is None:
        raise NotFoundError(f"No {kind.value} artifact for this session")

    return await gcs_utils.generate_signed_download_url(
        GCS_SN_BUCKET,
        artifact.storage_key,
        expiry_minutes=DOWNLOAD_URL_EXPIRY_MINUTES,
    )
