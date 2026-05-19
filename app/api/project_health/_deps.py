from __future__ import annotations

from fastapi import Depends, Header

from app.core.access_control import require_app_access, require_role
from app.core.auth_middleware import require_platform_admin
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.services.project_health.interview_token import (
    InterviewTokenClaims,
    decode_interview_token,
)

PH_APP_KEY = "project-health"
ph_access = require_app_access(PH_APP_KEY)
ph_admin = require_role(PH_APP_KEY, "admin")
ph_platform_admin = Depends(require_platform_admin)


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise AuthenticationError("Missing Authorization header")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        raise AuthenticationError("Invalid Authorization header")
    return parts[1]


async def require_interview_token(
    interview_id: str, authorization: str | None = Header(default=None)
) -> InterviewTokenClaims:
    token = _extract_bearer_token(authorization)
    claims = decode_interview_token(token)
    if claims.interview_id != interview_id:
        raise AuthorizationError("Interview token does not match interview id")
    return claims


interview_token_dep = Depends(require_interview_token)
