from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import AccessRequest, App, RefreshToken, Role, User, UserAppRole
from app.db.models.language import Language
from app.db.models.meaning_map import (
    BibleBook,
    MeaningMap,
    MeaningMapFeedback,
    Pericope,
)
from app.db.models.org import Organization, OrganizationMember
from app.db.models.phase import Phase, PhaseDependency, ProjectPhase
from app.db.models.project import (
    Project,
    ProjectOrganizationAccess,
    ProjectUserAccess,
)
from app.services.auth.hash_password import hash_password

SAMPLE_MM_DATA: dict = {
    "level_1": {"arc": "God creates the heavens and the earth."},
    "level_2_scenes": [
        {
            "scene_number": 1,
            "verses": "1-5",
            "title": "Creation of light",
            "people": [
                {
                    "name": "God",
                    "role": "Creator",
                    "relationship": "",
                    "wants": "to create",
                    "carries": "",
                }
            ],
            "places": [
                {
                    "name": "The void",
                    "role": "setting",
                    "type": "cosmic",
                    "meaning": "emptiness",
                    "effect_on_scene": "sets stage",
                }
            ],
            "objects": [
                {
                    "name": "Light",
                    "what_it_is": "illumination",
                    "function_in_scene": "first creation",
                    "signals": "goodness",
                }
            ],
            "significant_absence": "",
            "what_happens": ("God speaks light into existence and separates it from darkness."),
            "communicative_purpose": (
                "Establishes God as sovereign creator."
                " Shows the power of divine speech."
                " Introduces the pattern of creation by word."
            ),
        }
    ],
    "level_3_propositions": [
        {
            "proposition_number": 1,
            "verse": "1",
            "content": [
                {
                    "question": "What happens?",
                    "answer": "God creates the heavens and the earth.",
                }
            ],
        }
    ],
}


async def make_user(
    db: AsyncSession,
    *,
    email: str = "user@example.com",
    password: str = "password123",
    display_name: str | None = "Test User",
    is_active: bool = True,
    is_platform_admin: bool = False,
) -> User:
    user = User(
        email=email.lower(),
        password_hash=hash_password(password),
        display_name=display_name,
        is_active=is_active,
        is_platform_admin=is_platform_admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def make_app(
    db: AsyncSession,
    *,
    app_key: str = "test-app",
    name: str = "Test App",
    is_active: bool = True,
) -> App:
    app = App(app_key=app_key, name=name, is_active=is_active)
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


async def make_role(
    db: AsyncSession,
    app_id: str,
    *,
    role_key: str = "member",
    label: str = "Member",
    description: str | None = None,
    is_system: bool = False,
) -> Role:
    role = Role(
        app_id=app_id,
        role_key=role_key,
        label=label,
        description=description,
        is_system=is_system,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


async def make_user_app_role(
    db: AsyncSession,
    user_id: str,
    app_id: str,
    role_id: str,
    *,
    granted_by: str | None = None,
    revoked_at: datetime | None = None,
) -> UserAppRole:
    assignment = UserAppRole(
        user_id=user_id,
        app_id=app_id,
        role_id=role_id,
        granted_by=granted_by,
        revoked_at=revoked_at,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment


async def make_language(
    db: AsyncSession,
    *,
    name: str = "Test Language",
    code: str = "tst",
) -> Language:
    lang = Language(name=name, code=code.lower())
    db.add(lang)
    await db.commit()
    await db.refresh(lang)
    return lang


async def make_organization(
    db: AsyncSession,
    *,
    name: str = "Test Org",
    slug: str = "test-org",
) -> Organization:
    org = Organization(name=name, slug=slug.lower())
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


async def make_organization_member(
    db: AsyncSession,
    user_id: str,
    organization_id: str,
    *,
    role: str = "member",
) -> OrganizationMember:
    member = OrganizationMember(
        user_id=user_id,
        organization_id=organization_id,
        role=role,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def make_project(
    db: AsyncSession,
    language_id: str,
    *,
    name: str = "Test Project",
    description: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    location_display_name: str | None = None,
) -> Project:
    project = Project(
        name=name,
        language_id=language_id,
        description=description,
        latitude=latitude,
        longitude=longitude,
        location_display_name=location_display_name,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def make_project_user_access(
    db: AsyncSession,
    project_id: str,
    user_id: str,
) -> ProjectUserAccess:
    access = ProjectUserAccess(project_id=project_id, user_id=user_id)
    db.add(access)
    await db.commit()
    await db.refresh(access)
    return access


async def make_project_organization_access(
    db: AsyncSession,
    project_id: str,
    organization_id: str,
) -> ProjectOrganizationAccess:
    access = ProjectOrganizationAccess(
        project_id=project_id,
        organization_id=organization_id,
    )
    db.add(access)
    await db.commit()
    await db.refresh(access)
    return access


async def make_phase(
    db: AsyncSession,
    *,
    name: str = "Test Phase",
    description: str | None = None,
    status: str = "pending",
) -> Phase:
    phase = Phase(name=name, description=description, status=status)
    db.add(phase)
    await db.commit()
    await db.refresh(phase)
    return phase


async def make_project_phase(
    db: AsyncSession,
    project_id: str,
    phase_id: str,
) -> ProjectPhase:
    link = ProjectPhase(project_id=project_id, phase_id=phase_id)
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


async def make_phase_dependency(
    db: AsyncSession,
    phase_id: str,
    depends_on_id: str,
) -> PhaseDependency:
    dep = PhaseDependency(phase_id=phase_id, depends_on_id=depends_on_id)
    db.add(dep)
    await db.commit()
    await db.refresh(dep)
    return dep


async def make_refresh_token(
    db: AsyncSession,
    user_id: str,
    *,
    token_hash: str = "a" * 64,
    expires_at: datetime | None = None,
    revoked_at: datetime | None = None,
) -> RefreshToken:
    if expires_at is None:
        expires_at = datetime.now(UTC) + timedelta(days=7)
    record = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        revoked_at=revoked_at,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def make_bible_book(
    db: AsyncSession,
    *,
    name: str = "Genesis",
    abbreviation: str = "Gen",
    testament: str = "OT",
    order: int = 1,
    chapter_count: int = 50,
    is_enabled: bool = True,
) -> BibleBook:
    book = BibleBook(
        name=name,
        abbreviation=abbreviation,
        testament=testament,
        order=order,
        chapter_count=chapter_count,
        is_enabled=is_enabled,
    )
    db.add(book)
    await db.commit()
    await db.refresh(book)
    return book


async def make_pericope(
    db: AsyncSession,
    book_id: str,
    *,
    chapter_start: int = 1,
    verse_start: int = 1,
    chapter_end: int = 1,
    verse_end: int = 5,
    reference: str = "Gen 1:1-5",
    title: str | None = None,
) -> Pericope:
    pericope = Pericope(
        book_id=book_id,
        chapter_start=chapter_start,
        verse_start=verse_start,
        chapter_end=chapter_end,
        verse_end=verse_end,
        reference=reference,
        title=title,
    )
    db.add(pericope)
    await db.commit()
    await db.refresh(pericope)
    return pericope


async def make_meaning_map(
    db: AsyncSession,
    pericope_id: str,
    analyst_id: str,
    *,
    data: dict | None = None,
    status: str = "draft",
    locked_by: str | None = None,
    locked_at: datetime | None = None,
    version: int = 1,
) -> MeaningMap:
    mm = MeaningMap(
        pericope_id=pericope_id,
        analyst_id=analyst_id,
        data=data if data is not None else {},
        status=status,
        locked_by=locked_by,
        locked_at=locked_at,
        version=version,
    )
    db.add(mm)
    await db.commit()
    await db.refresh(mm)
    return mm


async def make_meaning_map_feedback(
    db: AsyncSession,
    meaning_map_id: str,
    author_id: str,
    *,
    section_key: str = "level_1.arc",
    content: str = "Needs more detail",
    resolved: bool = False,
) -> MeaningMapFeedback:
    fb = MeaningMapFeedback(
        meaning_map_id=meaning_map_id,
        section_key=section_key,
        author_id=author_id,
        content=content,
        resolved=resolved,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    return fb


async def make_access_request(
    db: AsyncSession,
    user_id: str,
    app_id: str,
    *,
    status: str = "pending",
    note: str | None = None,
) -> AccessRequest:
    req = AccessRequest(
        user_id=user_id,
        app_id=app_id,
        status=status,
        note=note,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req
