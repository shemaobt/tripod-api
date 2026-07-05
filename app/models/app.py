from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Platform = Literal["web", "android", "ios"]


def _default_platforms() -> list[Platform]:
    return ["web"]


class AppCreate(BaseModel):
    app_key: str
    name: str
    description: str | None = None
    icon_url: str | None = None
    app_url: str | None = None
    ios_url: str | None = None
    android_url: str | None = None
    platforms: list[Platform] = Field(default_factory=_default_platforms)
    is_active: bool | None = True
    auto_approve: bool | None = False


class AppUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon_url: str | None = None
    app_url: str | None = None
    ios_url: str | None = None
    android_url: str | None = None
    platforms: list[Platform] | None = None
    is_active: bool | None = None
    auto_approve: bool | None = None


class AppResponse(BaseModel):
    id: str
    app_key: str
    name: str
    description: str | None
    icon_url: str | None
    app_url: str | None
    ios_url: str | None
    android_url: str | None
    platforms: list[str]
    is_active: bool
    auto_approve: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserAppResponse(BaseModel):
    id: str
    app_key: str
    name: str
    description: str | None
    icon_url: str | None
    app_url: str | None
    ios_url: str | None
    android_url: str | None
    platforms: list[str]
    is_active: bool
    created_at: datetime
    roles: list[str]
    is_platform_admin: bool = False


class AppRoleCreate(BaseModel):
    role_key: str
    label: str
    description: str | None = None


class AppRoleResponse(BaseModel):
    id: str
    role_key: str
    label: str
    description: str | None
    is_system: bool
    created_at: datetime

    model_config = {"from_attributes": True}
