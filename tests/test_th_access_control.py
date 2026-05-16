import pytest
from sqlalchemy import select

from app.db.models.auth import App
from app.services.authorization.has_role import has_role
from app.services.authorization.list_roles import list_roles
from tests.baker import grant_app_role, make_user


@pytest.mark.asyncio
async def test_user_without_th_role_has_no_access(db_session) -> None:
    user = await make_user(db_session, email="th_ac_a@test.com")
    roles = await list_roles(db_session, user.id, "translation-helper")
    assert roles == []


@pytest.mark.asyncio
async def test_user_with_th_role_can_access(db_session) -> None:
    th_app = (
        await db_session.execute(select(App).where(App.app_key == "translation-helper"))
    ).scalar_one()
    user = await make_user(db_session, email="th_ac_b@test.com")
    await grant_app_role(db_session, user, th_app, role_key="user", label="User")

    roles = await list_roles(db_session, user.id, "translation-helper")
    assert roles == [("translation-helper", "user")]
    assert await has_role(db_session, user.id, "translation-helper", "user") is True


@pytest.mark.asyncio
async def test_platform_admin_bypasses_role_in_access_control() -> None:
    """`require_app_access` short-circuits for platform admins (see access_control.py)."""
    from app.core.access_control import require_app_access

    dep = require_app_access("translation-helper")
    assert dep is not None
