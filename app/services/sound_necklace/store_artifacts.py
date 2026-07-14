import base64
import hashlib

import google_crc32c
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.db.models.sound_necklace import ArtifactKind, SnArtifact, SnSession
from app.services.oral_collector import gcs_utils
from app.services.sound_necklace.constants import (
    ARTIFACT_CONTENT_TYPES,
    ARTIFACT_FILENAMES,
    GCS_SN_BUCKET,
)


def storage_key(session: SnSession, kind: ArtifactKind) -> str:
    """Where one artifact's bytes live.

    The frozen filename (PRD §10) is the last segment on purpose: a browser following
    the download redirect derives the saved filename from the URL path, so the pipeline
    receives the name it expects without the API setting a header on bytes it never
    serves. The slug prefixes it so a facilitator who exports two stories does not end
    up staring at ``manifesto-contas (1).json``.
    """
    return f"sound-necklace/{session.id}/{session.slug}-{ARTIFACT_FILENAMES[kind]}"


async def store_artifacts(
    db: AsyncSession, session: SnSession, payloads: dict[ArtifactKind, bytes]
) -> list[SnArtifact]:
    """Hand the three artifacts to storage exactly as they arrived, and record custody.

    The payloads arrive as bytes and stay bytes. **Nothing here parses one.** PRD §10.5
    makes that a contract breach and not a style preference: a parse-and-reserialize is
    invisible in review — the output is still valid, plausible JSON — and fatal to the
    pipeline, which diffs these files byte for byte against a golden reference. Key
    order, whitespace, unicode escaping and the trailing newline are all part of the
    artifact.

    The upload sends a CRC32C that GCS validates server-side, so a corrupted transfer
    is rejected by storage and the object is never created. That checksum is kept, plus
    a sha256 of our own, so custody can be proven without trusting the storage provider.

    Every payload is checked before any of them is uploaded: a half-written triple is
    worse than a rejected one, because the pipeline would read it as complete.
    """
    for kind, data in payloads.items():
        if not data:
            raise ValidationError(f"The {kind.value} artifact is empty")

    artifacts = []
    for kind, data in payloads.items():
        key = storage_key(session, kind)
        content_type = ARTIFACT_CONTENT_TYPES[kind]
        await gcs_utils.upload_gcs_object(GCS_SN_BUCKET, key, data, content_type)

        artifact = await db.get(SnArtifact, (session.id, kind))
        if artifact is None:
            artifact = SnArtifact(session_id=session.id, kind=kind)
            db.add(artifact)
        artifact.storage_key = key
        artifact.size = len(data)
        artifact.crc32c = base64.b64encode(google_crc32c.Checksum(data).digest()).decode()
        artifact.sha256 = hashlib.sha256(data).hexdigest()
        artifact.content_type = content_type
        artifacts.append(artifact)

    await db.commit()
    return artifacts
