from app.services.oral_collector.constants import GCS_OC_BUCKET, GCS_OC_PROJECT

GCS_PUBLIC_BASE = f"https://storage.googleapis.com/{GCS_OC_BUCKET}/"


async def upload_gcs_blob(blob_name: str, data: bytes, content_type: str) -> str:
    """Upload data to GCS and return the public URL."""
    from google.cloud import storage

    client = storage.Client(project=GCS_OC_PROJECT)
    bucket = client.bucket(GCS_OC_BUCKET)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data, content_type=content_type)
    return f"{GCS_PUBLIC_BASE}{blob_name}"


async def copy_gcs_blob(source_name: str, dest_name: str) -> None:
    """Copy a blob within the OC bucket."""
    from google.cloud import storage

    client = storage.Client(project=GCS_OC_PROJECT)
    bucket = client.bucket(GCS_OC_BUCKET)
    source_blob = bucket.blob(source_name)
    bucket.copy_blob(source_blob, bucket, dest_name)


def blob_name_from_url(gcs_url: str) -> str | None:
    """Extract the blob name from a full GCS public URL."""
    if not gcs_url.startswith(GCS_PUBLIC_BASE):
        return None
    return gcs_url[len(GCS_PUBLIC_BASE) :]


def original_blob_name(blob_name: str) -> str:
    """Derive the backup blob name by inserting '_original' before the extension."""
    dot_idx = blob_name.rfind(".")
    if dot_idx == -1:
        return f"{blob_name}_original"
    return f"{blob_name[:dot_idx]}_original{blob_name[dot_idx:]}"
