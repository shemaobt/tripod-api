from app.services.oral_collector.constants import GCS_OC_BUCKET, GCS_OC_PROJECT


async def upload_gcs_blob(blob_name: str, data: bytes, content_type: str) -> str:
    """Upload data to GCS and return the public URL."""
    from google.cloud import storage

    client = storage.Client(project=GCS_OC_PROJECT)
    bucket = client.bucket(GCS_OC_BUCKET)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data, content_type=content_type)
    return f"https://storage.googleapis.com/{GCS_OC_BUCKET}/{blob_name}"
