from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import select

from app.db.models.auth import Role
from app.db.models.oc_acousteme import OC_AcoustemeArtifact  # noqa: F401 (create_all)
from app.db.models.sound_necklace import (  # noqa: F401 (create_all)
    SnArtifact,
    SnAudioRef,
    SnSession,
    SnSessionState,
    SnVoiceAnswer,
)
from tests.baker import make_app, make_role, make_user_app_role

APP_KEY = "sound-necklace"


@pytest.fixture()
async def sound_necklace_app(db_session):
    """The sound-necklace app registry row plus its two seeded roles."""
    app = await make_app(db_session, app_key=APP_KEY, name="Sound Necklace")
    await make_role(db_session, app.id, role_key="facilitator", label="Facilitator", is_system=True)
    await make_role(
        db_session, app.id, role_key="project_admin", label="Project Admin", is_system=True
    )
    return app


@pytest.fixture()
async def client(db_session):
    """An ASGI client whose handlers run against the test session.

    Mounts only the sound-necklace router (with the real exception handlers, so
    AuthorizationError → 403) to avoid the full app's lifespan/inngest startup.
    Exercises the real dependency chain (auth → require_app_access) that gates
    every route in the module.
    """
    from fastapi import FastAPI

    from app.api.sound_necklace import router as sound_necklace_router
    from app.core.database import get_db
    from app.core.exceptions import register_exception_handlers

    test_app = FastAPI()
    test_app.include_router(sound_necklace_router, prefix="/api/sound-necklace")
    register_exception_handlers(test_app)

    async def _get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = _get_db
    transport = ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def auth_header(db_session, user) -> dict[str, str]:
    """A real bearer token for ``user`` (decoded by the auth dependency)."""
    from app.services.auth.issue_tokens import issue_tokens

    access, _refresh = await issue_tokens(db_session, user)
    return {"Authorization": f"Bearer {access}"}


async def grant_role(db_session, app_id: str, user_id: str, role_key: str) -> None:
    """Assign an existing seeded role (facilitator/project_admin) to a user."""
    role = (
        await db_session.execute(
            select(Role).where(Role.app_id == app_id, Role.role_key == role_key)
        )
    ).scalar_one()
    await make_user_app_role(db_session, user_id, app_id, role.id)
