from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_middleware import get_current_user, require_platform_admin
from app.core.database import get_db
from app.db.models.auth import User
from app.models.app import (
    AppCreate,
    AppResponse,
    AppRoleCreate,
    AppRoleResponse,
    AppUpdate,
    UserAppResponse,
)
from app.services import app_service

router = APIRouter()


@router.get("", response_model=list[AppResponse])
async def list_apps(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> list[AppResponse]:
    apps = await app_service.list_apps(db)
    return [AppResponse.model_validate(a) for a in apps]


@router.get("/my-apps", response_model=list[UserAppResponse])
async def my_apps(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserAppResponse]:
    if current_user.is_platform_admin:
        # Platform admins see ALL active apps; merge their explicit roles if any
        all_apps = await app_service.list_apps(db)
        user_apps_map: dict[str, list[str]] = {}
        for app, role_keys in await app_service.list_user_apps(db, current_user.id):
            user_apps_map[app.id] = role_keys
        return [
            UserAppResponse(
                id=app.id,
                app_key=app.app_key,
                name=app.name,
                description=app.description,
                icon_url=app.icon_url,
                app_url=app.app_url,
                ios_url=app.ios_url,
                android_url=app.android_url,
                platform=app.platform,
                is_active=app.is_active,
                created_at=app.created_at,
                roles=user_apps_map.get(app.id, []),
                is_platform_admin=True,
            )
            for app in all_apps
        ]

    user_apps = await app_service.list_user_apps(db, current_user.id)
    return [
        UserAppResponse(
            id=app.id,
            app_key=app.app_key,
            name=app.name,
            description=app.description,
            icon_url=app.icon_url,
            app_url=app.app_url,
            ios_url=app.ios_url,
            android_url=app.android_url,
            platform=app.platform,
            is_active=app.is_active,
            created_at=app.created_at,
            roles=role_keys,
            is_platform_admin=False,
        )
        for app, role_keys in user_apps
    ]


@router.post("", response_model=AppResponse, status_code=201)
async def create_app(
    payload: AppCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> AppResponse:
    app = await app_service.create_app(
        db,
        app_key=payload.app_key,
        name=payload.name,
        description=payload.description,
        icon_url=payload.icon_url,
        app_url=payload.app_url,
        ios_url=payload.ios_url,
        android_url=payload.android_url,
        platform=payload.platform or "web",
        is_active=payload.is_active if payload.is_active is not None else True,
    )
    return AppResponse.model_validate(app)


@router.get("/{app_id}", response_model=AppResponse)
async def get_app(
    app_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AppResponse:
    app = await app_service.get_app_or_404(db, app_id)
    return AppResponse.model_validate(app)


@router.patch("/{app_id}", response_model=AppResponse)
async def update_app(
    app_id: str,
    payload: AppUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> AppResponse:
    app = await app_service.update_app(
        db,
        app_id,
        name=payload.name,
        description=payload.description,
        icon_url=payload.icon_url,
        app_url=payload.app_url,
        ios_url=payload.ios_url,
        android_url=payload.android_url,
        platform=payload.platform,
        is_active=payload.is_active,
    )
    return AppResponse.model_validate(app)


@router.delete("/{app_id}", status_code=204)
async def delete_app(
    app_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> None:
    await app_service.delete_app(db, app_id)


@router.get("/{app_id}/roles", response_model=list[AppRoleResponse])
async def list_app_roles(
    app_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AppRoleResponse]:
    roles = await app_service.list_app_roles(db, app_id)
    return [AppRoleResponse.model_validate(r) for r in roles]


@router.post("/{app_id}/roles", response_model=AppRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_app_role(
    app_id: str,
    payload: AppRoleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> AppRoleResponse:
    role = await app_service.create_app_role(
        db, app_id, role_key=payload.role_key, label=payload.label, description=payload.description,
    )
    return AppRoleResponse.model_validate(role)


@router.delete("/{app_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_app_role(
    app_id: str,
    role_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> None:
    await app_service.delete_app_role(db, app_id, role_id)
