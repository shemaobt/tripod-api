from datetime import datetime

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=100)


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(default=None, min_length=1, max_length=100)


class OrganizationMemberAdd(BaseModel):
    user_id: str
    role: str = Field(default="member", max_length=50)


class OrganizationMemberResponse(BaseModel):
    id: str
    user_id: str
    organization_id: str
    role: str
    joined_at: datetime

    model_config = {"from_attributes": True}


class OrganizationMemberDetailResponse(BaseModel):
    id: str
    user_id: str
    organization_id: str
    role: str
    joined_at: datetime
    email: str
    display_name: str | None
