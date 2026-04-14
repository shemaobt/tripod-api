from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Sex = Literal["male", "female"]


class StorytellerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    sex: Sex
    age: int | None = Field(default=None, ge=0, le=150)
    location: str | None = Field(default=None, max_length=500)
    dialect: str | None = Field(default=None, max_length=500)
    external_acceptance_confirmed: bool

    @field_validator("external_acceptance_confirmed")
    @classmethod
    def _must_be_true(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "External acceptance validation is required before registering a storyteller"
            )
        return v


class StorytellerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    sex: Sex | None = None
    age: int | None = Field(default=None, ge=0, le=150)
    location: str | None = Field(default=None, max_length=500)
    dialect: str | None = Field(default=None, max_length=500)


class StorytellerResponse(BaseModel):
    id: str
    project_id: str
    name: str
    sex: str
    age: int | None = None
    location: str | None = None
    dialect: str | None = None
    external_acceptance_confirmed: bool
    external_acceptance_confirmed_at: datetime | None = None
    external_acceptance_confirmed_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
