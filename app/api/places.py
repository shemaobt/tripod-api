import httpx
from fastapi import APIRouter, Depends, Query

from app.core.auth_middleware import get_current_user
from app.core.config import get_settings
from app.db.models.auth import User

router = APIRouter()

PLACES_AUTOCOMPLETE_URL = "https://places.googleapis.com/v1/places:autocomplete"
PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places"


@router.get("/autocomplete")
async def places_autocomplete(
    q: str = Query(..., min_length=1),
    _: User = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            PLACES_AUTOCOMPLETE_URL,
            json={"input": q},
            headers={
                "X-Goog-Api-Key": settings.google_maps_api_key,
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )
        return resp.json()


@router.get("/details")
async def place_details(
    place_id: str = Query(...),
    _: User = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{PLACE_DETAILS_URL}/{place_id}",
            headers={
                "X-Goog-Api-Key": settings.google_maps_api_key,
                "X-Goog-FieldMask": "displayName,formattedAddress,location",
            },
            timeout=10.0,
        )
        return resp.json()
