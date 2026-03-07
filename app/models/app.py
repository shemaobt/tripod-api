from datetime import datetime

from pydantic import BaseModel


class AppCreate(BaseModel):
    app_key: str
    name: str
    description: str | None = None
    icon_url: str | None = None
    app_url: str | None = None
    ios_url: str | None = None
    android_url: str | None = None
    platform: str | None = "web"
    is_active: bool | None = True


class AppUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon_url: str | None = None
    app_url: str | None = None
    ios_url: str | None = None
    android_url: str | None = None
    platform: str | None = None
    is_active: bool | None = None


class AppResponse(BaseModel):
    id: str
    app_key: str
    name: str
    description: str | None
    icon_url: str | None
    app_url: str | None
    ios_url: str | None
    android_url: str | None
    platform: str
    is_active: bool
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
    platform: str
    is_active: bool
    created_at: datetime
    roles: list[str]


class AppRoleResponse(BaseModel):
    id: str
    role_key: str
    label: str
    description: str | None
    is_system: bool
    created_at: datetime

    model_config = {"from_attributes": True}
