from datetime import datetime

from pydantic import BaseModel


class UserListResponse(BaseModel):
    id: str
    email: str
    display_name: str | None
    is_active: bool
    is_platform_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    is_active: bool | None = None
    is_platform_admin: bool | None = None


class UserRoleResponse(BaseModel):
    app_key: str
    role_key: str
    granted_at: datetime
