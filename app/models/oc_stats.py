from pydantic import BaseModel


class GenreStatItem(BaseModel):
    genre_id: str
    genre_name: str
    recording_count: int
    duration_seconds: float


class SubcategoryStatItem(BaseModel):
    subcategory_id: str
    subcategory_name: str
    genre_id: str
    recording_count: int
    duration_seconds: float


class GenreStatsResponse(BaseModel):
    project_id: str
    genres: list[GenreStatItem]
    subcategories: list[SubcategoryStatItem]


class AdminStatsResponse(BaseModel):
    total_projects: int
    total_languages: int
    total_hours: float
    active_users: int
