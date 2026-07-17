from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.project import ProjectBaseResponse


class OCProjectListResponse(ProjectBaseResponse):
    member_count: int = 0
    recording_count: int = 0
    total_duration_seconds: float = 0.0
    storyteller_count: int = 0


class OCProjectStatsResponse(BaseModel):
    project_id: str
    total_recordings: int
    total_duration_seconds: float
    total_file_size_bytes: int
    total_storytellers: int = 0


class OCProjectInviteCreate(BaseModel):
    email: EmailStr
    role: str = Field(default="member", max_length=30)


class OCProjectInviteResponse(BaseModel):
    id: str
    project_id: str
    project_name: str | None = None
    email: str
    invited_by: str
    status: str
    role: str
    app_key: str | None = None
    created_at: datetime
    accepted_at: datetime | None

    model_config = {"from_attributes": True}
