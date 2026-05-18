import pytest
from sqlalchemy import select

from app.db.models.auth import App
from app.services.access_request._default_roles import (
    DEFAULT_ROLE_BY_APP_KEY,
    default_role_for,
)
from app.services.access_request.review_access_request import review_access_request
from app.services.authorization.has_role import has_role
from app.services.authorization.list_roles import list_roles
from tests.baker import grant_app_role, make_access_request, make_role, make_user


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


def test_default_role_map_pins_translation_helper_to_user() -> None:
    assert DEFAULT_ROLE_BY_APP_KEY["translation-helper"] == "user"
    assert default_role_for("translation-helper") == "user"
    assert default_role_for("meaning-map-generator") == "analyst"
    assert default_role_for("some-unknown-app") == "analyst"


@pytest.mark.asyncio
async def test_review_approve_grants_user_role_for_translation_helper(db_session) -> None:
    """Smoke-tests the full request→approve→access path for translation-helper.

    Regression guard: approval previously hardcoded `"analyst"`, which doesn't
    exist for translation-helper, so approval raised RoleError. Now dispatched
    via DEFAULT_ROLE_BY_APP_KEY.
    """
    th_app = (
        await db_session.execute(select(App).where(App.app_key == "translation-helper"))
    ).scalar_one()
    await make_role(db_session, th_app.id, role_key="user", label="User", is_system=True)

    requester = await make_user(db_session, email="th_req@test.com")
    admin = await make_user(db_session, email="th_admin@test.com", is_platform_admin=True)
    access_request = await make_access_request(db_session, requester.id, th_app.id)

    reviewed = await review_access_request(db_session, admin, access_request.id, status="approved")
    assert reviewed.status == "approved"

    granted_roles = await list_roles(db_session, requester.id, "translation-helper")
    assert granted_roles == [("translation-helper", "user")]


@pytest.mark.asyncio
async def test_review_approve_grants_analyst_role_for_meaning_map(db_session) -> None:
    """Mirror of the TH test — confirms the legacy meaning-map flow is unbroken."""
    mm_app = (
        await db_session.execute(select(App).where(App.app_key == "meaning-map-generator"))
    ).scalar_one()
    await make_role(db_session, mm_app.id, role_key="analyst", label="Analyst", is_system=True)

    requester = await make_user(db_session, email="mm_req@test.com")
    admin = await make_user(db_session, email="mm_admin@test.com", is_platform_admin=True)
    access_request = await make_access_request(db_session, requester.id, mm_app.id)

    reviewed = await review_access_request(db_session, admin, access_request.id, status="approved")
    assert reviewed.status == "approved"

    granted_roles = await list_roles(db_session, requester.id, "meaning-map-generator")
    assert granted_roles == [("meaning-map-generator", "analyst")]
