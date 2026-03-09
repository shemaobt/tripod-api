from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_cache import invalidate_user
from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.db.models.auth import User
from app.models.auth import (
    AuthResponse,
    ProfileUpdate,
    TokenRefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserResponse,
    UserSignupRequest,
)
from app.models.role import MyRoleResponse
from app.services import auth_service, authorization_service

router = APIRouter()


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_platform_admin=user.is_platform_admin,
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserSignupRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    user = await auth_service.signup_user(db, payload)
    access_token, refresh_token = await auth_service.issue_tokens(db, user)
    return AuthResponse(
        user=_user_response(user),
        tokens=TokenResponse(access_token=access_token, refresh_token=refresh_token),
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: UserLoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    user = await auth_service.authenticate_user(db, payload.email, payload.password)
    access_token, refresh_token = await auth_service.issue_tokens(db, user)
    return AuthResponse(
        user=_user_response(user),
        tokens=TokenResponse(access_token=access_token, refresh_token=refresh_token),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: TokenRefreshRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    access_token = await auth_service.refresh_access_token(db, payload.refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: TokenRefreshRequest, db: AsyncSession = Depends(get_db)) -> None:
    await auth_service.revoke_refresh_token(db, payload.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    return _user_response(user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    user = await db.get(User, current_user.id)
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url if payload.avatar_url else None
    await db.commit()
    await db.refresh(user)
    invalidate_user(user.id)
    return _user_response(user)


@router.get("/my-roles", response_model=list[MyRoleResponse])
async def my_roles(
    app_key: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MyRoleResponse]:
    roles = await authorization_service.list_roles(db, user.id, app_key)
    return [MyRoleResponse(app_key=entry[0], role_key=entry[1]) for entry in roles]
