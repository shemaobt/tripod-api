"""Shared dependencies for sound-necklace routers.

``CurrentUser`` requires any sound-necklace role (or platform admin), gating the
whole ``/api/sound-necklace`` surface via the shared per-app RBAC guard.
Role-specific guards (facilitator / project_admin) and the ``Db`` session alias
are added when a route needs them.
"""

from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import HTTPException, status

from app.core.access_control import require_app_access
from app.db.models.auth import User

APP_KEY = "sound-necklace"

CurrentUser = Annotated[User, require_app_access(APP_KEY)]


def not_implemented() -> NoReturn:
    """Signal a route that is still a contract stub."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet.",
    )
