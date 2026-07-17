"""Shared dependencies for sound-necklace routers.

``CurrentUser`` requires any sound-necklace role (or platform admin), gating the
whole ``/api/sound-necklace`` surface via the shared per-app RBAC guard.
Role-specific guards (facilitator / project_admin) are added when a route needs
them.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_app_access
from app.core.database import get_db
from app.core.exceptions import ERROR_CODE_SESSION_LOCKED
from app.db.models.auth import User
from app.services.sound_necklace.lock_fence import SessionLockedByOther

APP_KEY = "sound-necklace"

CurrentUser = Annotated[User, require_app_access(APP_KEY)]
Db = Annotated[AsyncSession, Depends(get_db)]

LOCKED_RESPONSE: dict[int | str, dict[str, Any]] = {
    status.HTTP_409_CONFLICT: {
        "description": (
            "Somebody else holds the editor lock; the body carries holder_name and "
            "expires_at, and `code` is SESSION_LOCKED."
        )
    }
}


def locked_body(exc: SessionLockedByOther) -> JSONResponse:
    """The 409 the lease raises, built by hand on every route that can raise it.

    The global ConflictError handler emits {detail, code} and constructs a fresh
    response, so the holder and expiry would not survive it.
    """
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": str(exc),
            "code": ERROR_CODE_SESSION_LOCKED,
            "holder_name": exc.holder_name,
            "expires_at": exc.expires_at.isoformat(),
        },
    )
