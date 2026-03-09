import uuid

from fastapi import UploadFile

GCS_UPLOADS_BUCKET = "tripod-image-uploads"
GCS_PROJECT = "gen-lang-client-0886209230"

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/svg+xml"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


async def upload_image(file: UploadFile, folder: str = "images") -> str:
    from google.cloud import storage  # type: ignore[import-untyped]

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(f"Unsupported file type: {file.content_type}")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise ValueError("File size exceeds 5 MB limit")

    ext = _extension_for(file.content_type)
    blob_name = f"{folder}/{uuid.uuid4().hex}{ext}"

    client = storage.Client(project=GCS_PROJECT)
    bucket = client.bucket(GCS_UPLOADS_BUCKET)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(contents, content_type=file.content_type)

    return f"https://storage.googleapis.com/{GCS_UPLOADS_BUCKET}/{blob_name}"


def _extension_for(content_type: str | None) -> str:
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
    }
    return mapping.get(content_type or "", ".bin")
