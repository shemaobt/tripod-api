from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class PublicLanguageOption(BaseModel):
    id: str
    name: str
    code: str

    model_config = {"from_attributes": True}


class PublicLanguageRequestCreate(BaseModel):
    requester_name: str = Field(min_length=1, max_length=200)
    requester_email: EmailStr
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=3, max_length=3)
    recaptcha_token: str = Field(min_length=1)


class PublicProjectRequestCreate(BaseModel):
    requester_name: str = Field(min_length=1, max_length=200)
    requester_email: EmailStr
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    language_id: str
    recaptcha_token: str = Field(min_length=1)


class PublicRequestResponse(BaseModel):
    id: str
    kind: str
    status: str
    requester_name: str
    requester_email: str
    name: str
    code: str | None
    description: str | None
    language_id: str | None
    requested_at: datetime

    model_config = {"from_attributes": True}
