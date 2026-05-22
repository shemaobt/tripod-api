import asyncio

from google.cloud import storage

from app.services.oral_collector.constants import GCS_OC_BUCKET, GCS_OC_PROJECT

GCS_PUBLIC_BASE = f"https://storage.googleapis.com/{GCS_OC_BUCKET}/"


async def upload_gcs_blob(blob_name: str, data: bytes, content_type: str) -> str:
    def _blocking() -> str:
        client = storage.Client(project=GCS_OC_PROJECT)
        bucket = client.bucket(GCS_OC_BUCKET)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(data, content_type=content_type)
        return f"{GCS_PUBLIC_BASE}{blob_name}"

    return await asyncio.to_thread(_blocking)


async def copy_gcs_blob(source_name: str, dest_name: str) -> None:
    def _blocking() -> None:
        client = storage.Client(project=GCS_OC_PROJECT)
        bucket = client.bucket(GCS_OC_BUCKET)
        source_blob = bucket.blob(source_name)
        bucket.copy_blob(source_blob, bucket, dest_name)

    await asyncio.to_thread(_blocking)


def blob_name_from_url(gcs_url: str) -> str | None:
    if not gcs_url.startswith(GCS_PUBLIC_BASE):
        return None
    return gcs_url[len(GCS_PUBLIC_BASE) :]


def original_blob_name(blob_name: str) -> str:
    dot_idx = blob_name.rfind(".")
    if dot_idx == -1:
        return f"{blob_name}_original"
    return f"{blob_name[:dot_idx]}_original{blob_name[dot_idx:]}"


def content_type_for_format(fmt: str) -> str:
    mapping = {
        "m4a": "audio/mp4",
        "aac": "audio/aac",
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "webm": "audio/webm",
    }
    return mapping.get(fmt.lower(), "application/octet-stream")
