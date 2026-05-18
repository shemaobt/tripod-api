from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

INTERVIEW_TOKEN_AUDIENCE = "ph_interview"
INTERVIEW_TOKEN_TTL = timedelta(hours=24)


@dataclass(frozen=True)
class InterviewTokenClaims:
    interview_id: str
    issued_at: datetime
    expires_at: datetime


def encode_interview_token(
    interview_id: str, *, ttl: timedelta = INTERVIEW_TOKEN_TTL
) -> tuple[str, datetime]:
    settings = get_settings()
    now = datetime.now(UTC)
    expires_at = now + ttl
    payload = {
        "sub": interview_id,
        "aud": INTERVIEW_TOKEN_AUDIENCE,
        "jti": str(uuid4()),
        "iat": now,
        "exp": expires_at,
    }
    token = str(
        jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    )
    return token, expires_at


def decode_interview_token(token: str) -> InterviewTokenClaims:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=INTERVIEW_TOKEN_AUDIENCE,
        )
    except JWTError as exc:
        raise AuthenticationError("Invalid or expired interview token") from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise AuthenticationError("Interview token missing subject")

    iat = payload.get("iat")
    exp = payload.get("exp")
    return InterviewTokenClaims(
        interview_id=subject,
        issued_at=datetime.fromtimestamp(int(iat), UTC) if iat else datetime.now(UTC),
        expires_at=datetime.fromtimestamp(int(exp), UTC) if exp else datetime.now(UTC),
    )
