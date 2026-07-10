import httpx

from app.core.config import get_settings
from app.core.exceptions import ValidationError

RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"


async def _siteverify(secret: str, token: str) -> bool:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            RECAPTCHA_VERIFY_URL,
            data={"secret": secret, "response": token},
        )
        response.raise_for_status()
        payload = response.json()
    return bool(payload.get("success"))


async def verify_recaptcha(token: str) -> None:
    secret = get_settings().recaptcha_secret_key
    if not secret:
        return
    if not await _siteverify(secret, token):
        raise ValidationError("reCAPTCHA verification failed")
