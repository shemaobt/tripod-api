from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models.translation_helper import AgentId, ChatMessageRole


class ChatCreate(BaseModel):
    agent_id: AgentId = AgentId.STORYTELLER
    title: str | None = Field(default=None, max_length=100)


class ChatUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=100)
    agent_id: AgentId | None = None


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1)
    agent_id: AgentId | None = None


class ChatMessageResponse(BaseModel):
    id: str
    chat_id: str
    role: ChatMessageRole
    content: str
    agent_id: AgentId | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatListResponse(BaseModel):
    id: str
    user_id: str
    agent_id: AgentId
    title: str | None
    created_at: datetime
    updated_at: datetime
    last_message_preview: str | None = None
    last_message_at: datetime | None = None

    model_config = {"from_attributes": True}


class ChatResponse(ChatListResponse):
    messages: list[ChatMessageResponse] = Field(default_factory=list)


class AgentPromptResponse(BaseModel):
    id: str
    agent_id: AgentId
    name: str
    description: str
    prompt: str
    version: int
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentPromptUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    description: str | None = None
    prompt: str | None = Field(default=None, min_length=1)


class AgentInfoResponse(BaseModel):
    id: AgentId
    name: str
    description: str
    short: str
    icon: str
    starters: list[str]
    prompt_version: int | None = None


class TranscribeResponse(BaseModel):
    text: str
    duration_sec: float | None = None


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    language_code: str = Field(default="en-US", max_length=20)
    voice_name: str | None = Field(default=None, max_length=80)


class SpeakResponse(BaseModel):
    audio_base64: str
    mime_type: str = "audio/mpeg"
    etag: str
    cached: bool = False
