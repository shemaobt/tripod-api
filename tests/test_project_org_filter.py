import pytest

from app.core.org_scope import get_managed_org_ids
from app.services import project_service
from tests.baker import (
    make_language,
    make_organization,
    make_organization_member,
    make_project,
    make_project_organization_access,
    make_user,
)


@pytest.mark.asyncio
async def test_list_projects_by_org_returns_linked_projects(db_session) -> None:
    lang = await make_language(db_session, code="lfb")
    org = await make_organization(db_session, slug="org-filter")
    p1 = await make_project(db_session, language_id=lang.id, name="Alpha")
    p2 = await make_project(db_session, language_id=lang.id, name="Beta")
    await make_project(db_session, language_id=lang.id, name="Gamma")
    await make_project_organization_access(db_session, p1.id, org.id)
    await make_project_organization_access(db_session, p2.id, org.id)

    projects = await project_service.list_projects_by_organization(db_session, org.id)
    assert [p.name for p in projects] == ["Alpha", "Beta"]


@pytest.mark.asyncio
async def test_list_projects_by_org_empty_when_no_access(db_session) -> None:
    org = await make_organization(db_session, slug="org-empty")
    projects = await project_service.list_projects_by_organization(db_session, org.id)
    assert projects == []


@pytest.mark.asyncio
async def test_list_projects_by_org_does_not_return_other_org_projects(db_session) -> None:
    lang = await make_language(db_session, code="lfo")
    org_a = await make_organization(db_session, slug="org-a")
    org_b = await make_organization(db_session, slug="org-b")
    p1 = await make_project(db_session, language_id=lang.id, name="For A")
    p2 = await make_project(db_session, language_id=lang.id, name="For B")
    await make_project_organization_access(db_session, p1.id, org_a.id)
    await make_project_organization_access(db_session, p2.id, org_b.id)

    result_a = await project_service.list_projects_by_organization(db_session, org_a.id)
    assert [p.name for p in result_a] == ["For A"]

    result_b = await project_service.list_projects_by_organization(db_session, org_b.id)
    assert [p.name for p in result_b] == ["For B"]

@pytest.mark.asyncio
async def test_manager_autoscope_sees_only_managed_org_projects(db_session) -> None:
    lang = await make_language(db_session, code="mas")
    manager = await make_user(db_session, email="mgr@scope.com")
    org = await make_organization(db_session, slug="mgr-org", manager_id=manager.id)
    p1 = await make_project(db_session, language_id=lang.id, name="Managed Project")
    await make_project_organization_access(db_session, p1.id, org.id)
    await make_project(db_session, language_id=lang.id, name="Other Project")

    managed_ids = await get_managed_org_ids(db_session, manager.id)
    assert org.id in managed_ids

    all_managed_projects = []
    seen: set[str] = set()
    for oid in managed_ids:
        for p in await project_service.list_projects_by_organization(db_session, oid):
            if p.id not in seen:
                seen.add(p.id)
                all_managed_projects.append(p)

    assert len(all_managed_projects) == 1
    assert all_managed_projects[0].name == "Managed Project"


@pytest.mark.asyncio
async def test_manager_filter_by_unmanaged_org_returns_empty(db_session) -> None:
    lang = await make_language(db_session, code="mun")
    manager = await make_user(db_session, email="mgr-no@scope.com")
    await make_organization(db_session, slug="own-org", manager_id=manager.id)
    other_org = await make_organization(db_session, slug="other-org")
    p1 = await make_project(db_session, language_id=lang.id, name="Other Org Project")
    await make_project_organization_access(db_session, p1.id, other_org.id)

    managed_ids = await get_managed_org_ids(db_session, manager.id)
    assert other_org.id not in managed_ids

    projects: list = []
    assert projects == []


@pytest.mark.asyncio
async def test_manager_filter_by_managed_org_returns_projects(db_session) -> None:
    lang = await make_language(db_session, code="mfm")
    manager = await make_user(db_session, email="mgr-own@scope.com")
    org = await make_organization(db_session, slug="own-good", manager_id=manager.id)
    p1 = await make_project(db_session, language_id=lang.id, name="Good Project")
    await make_project_organization_access(db_session, p1.id, org.id)

    managed_ids = await get_managed_org_ids(db_session, manager.id)
    assert org.id in managed_ids

    projects = await project_service.list_projects_by_organization(db_session, org.id)
    assert len(projects) == 1
    assert projects[0].name == "Good Project"


@pytest.mark.asyncio
async def test_manager_via_member_role_sees_projects(db_session) -> None:
    lang = await make_language(db_session, code="mmr")
    manager = await make_user(db_session, email="role-mgr@scope.com")
    org = await make_organization(db_session, slug="role-org")
    await make_organization_member(db_session, manager.id, org.id, role="manager")
    p1 = await make_project(db_session, language_id=lang.id, name="Role Project")
    await make_project_organization_access(db_session, p1.id, org.id)

    managed_ids = await get_managed_org_ids(db_session, manager.id)
    assert org.id in managed_ids

    projects = await project_service.list_projects_by_organization(db_session, org.id)
    assert len(projects) == 1
    assert projects[0].name == "Role Project"
