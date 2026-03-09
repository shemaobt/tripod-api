from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.core.auth_middleware import get_current_user
from app.db.models.auth import User
from app.services.storage import upload_image

router = APIRouter()


@router.post("/image")
async def upload_image_endpoint(
    file: UploadFile,
    folder: str = "images",
    _: User = Depends(get_current_user),
) -> dict[str, str]:
    if folder not in ("app-icons", "avatars", "images"):
        folder = "images"
    try:
        url = await upload_image(file, folder=folder)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return {"url": url}
