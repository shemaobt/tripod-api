"""Bootstrap proof for the Sound Necklace (Colar de Sons) module: the app + roles
are seeded, and ``require_app_access`` gates the whole ``/api/colar`` surface.
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.models.auth import App, Role
from scripts.seed_apps_roles import APP_ROLES_OVERRIDE, SEED_APPS
from tests.baker import make_user
from tests.test_colar.conftest import APP_KEY, auth_header, grant_role

COLAR = "/api/colar"


async def test_app_and_roles_are_seeded(db_session, colar_app):
    app = (await db_session.execute(select(App).where(App.app_key == APP_KEY))).scalar_one()
    role_keys = set(
        (await db_session.execute(select(Role.role_key).where(Role.app_id == app.id)))
        .scalars()
        .all()
    )
    assert {"facilitator", "project_admin"} <= role_keys


def test_seed_script_registers_sound_necklace():
    """The real seed script (not just the test fixture) provisions the app + roles."""
    assert any(entry[0] == APP_KEY for entry in SEED_APPS)
    assert APP_ROLES_OVERRIDE[APP_KEY] == ["facilitator", "project_admin"]


async def test_unauthenticated_request_is_rejected(client, colar_app):
    res = await client.get(f"{COLAR}/sessions")
    assert res.status_code == 401


async def test_authenticated_without_app_access_is_forbidden(client, db_session, colar_app):
    outsider = await make_user(db_session, email="outsider@example.com")
    headers = await auth_header(db_session, outsider)
    res = await client.get(f"{COLAR}/sessions", headers=headers)
    assert res.status_code == 403


async def test_member_passes_the_gate_and_reaches_the_stub(client, db_session, colar_app):
    member = await make_user(db_session, email="member@example.com")
    await grant_role(db_session, colar_app.id, member.id, "facilitator")
    headers = await auth_header(db_session, member)
    res = await client.get(f"{COLAR}/sessions", headers=headers)
    # Gate passed → reaches the not-yet-implemented stub.
    assert res.status_code == 501
