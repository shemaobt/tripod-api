"""Shared dependencies for sound-necklace routers.

``CurrentUser`` requires any sound-necklace role (or platform admin), gating the
whole ``/api/sound-necklace`` surface via the shared per-app RBAC guard.
Role-specific guards (facilitator / project_admin) are added when a route needs
them.
"""

from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_app_access
from app.core.database import get_db
from app.db.models.auth import User

APP_KEY = "sound-necklace"

CurrentUser = Annotated[User, require_app_access(APP_KEY)]
Db = Annotated[AsyncSession, Depends(get_db)]


def not_implemented() -> NoReturn:
    """Signal a route that is still a contract stub."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet.",
    )
