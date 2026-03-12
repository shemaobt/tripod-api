from datetime import datetime

from pydantic import BaseModel, Field


class SubcategoryResponse(BaseModel):
    id: str
    genre_id: str
    name: str
    description: str | None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubcategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    sort_order: int = 0


class SubcategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    sort_order: int | None = None
    is_active: bool | None = None


class GenreResponse(BaseModel):
    id: str
    name: str
    description: str | None
    icon: str | None
    color: str | None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    subcategories: list[SubcategoryResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class GenreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    icon: str | None = Field(default=None, max_length=100)
    color: str | None = Field(default=None, max_length=20)
    sort_order: int = 0


class GenreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    icon: str | None = Field(default=None, max_length=100)
    color: str | None = Field(default=None, max_length=20)
    sort_order: int | None = None
    is_active: bool | None = None
