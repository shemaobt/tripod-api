"""Shared dependencies for Sound Necklace (Colar de Sons) routers.

``CurrentUser`` requires any sound-necklace role (or platform admin), gating the
whole ``/api/colar`` surface via the shared per-app RBAC guard. Role-specific
guards (facilitator / project_admin) are added by the resource issues that need
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

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, require_app_access(APP_KEY)]


def not_implemented() -> NoReturn:
    """Every Colar route is a contract stub until its own resource issue lands."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet — lands with this resource's own issue.",
    )
