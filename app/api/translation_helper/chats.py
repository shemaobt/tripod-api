import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.translation_helper._deps import th_access
from app.core.auth_middleware import get_current_user
from app.core.database import AsyncSessionLocal, get_db
from app.db.models.auth import User
from app.models.translation_helper import (
    ChatCreate,
    ChatListResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatResponse,
    ChatUpdate,
)
from app.services import translation_helper_service as th_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/chats", response_model=list[ChatListResponse], dependencies=[th_access])
async def list_chats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChatListResponse]:
    rows = await th_service.list_chats_for_user(db, user.id)
    return [ChatListResponse.model_validate(r) for r in rows]


@router.post(
    "/chats",
    response_model=ChatListResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[th_access],
)
async def create_chat(
    payload: ChatCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatListResponse:
    chat = await th_service.create_chat(db, user.id, agent_id=payload.agent_id, title=payload.title)
    return ChatListResponse.model_validate(chat)


@router.get("/chats/{chat_id}", response_model=ChatResponse, dependencies=[th_access])
async def get_chat(
    chat_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    chat = await th_service.get_chat_or_404(db, chat_id, user_id=user.id)
    messages = await th_service.list_messages(db, chat.id)
    return ChatResponse(
        id=chat.id,
        user_id=chat.user_id,
        agent_id=chat.agent_id,
        title=chat.title,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        last_message_at=messages[-1].created_at if messages else None,
        last_message_preview=(messages[-1].content[:120] if messages else None),
        messages=[ChatMessageResponse.model_validate(m) for m in messages],
    )


@router.patch("/chats/{chat_id}", response_model=ChatListResponse, dependencies=[th_access])
async def update_chat(
    chat_id: str,
    payload: ChatUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatListResponse:
    chat = await th_service.update_chat(
        db, chat_id, user.id, title=payload.title, agent_id=payload.agent_id
    )
    return ChatListResponse.model_validate(chat)


@router.delete(
    "/chats/{chat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[th_access],
)
async def delete_chat(
    chat_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await th_service.delete_chat(db, chat_id, user.id)


@router.get(
    "/chats/{chat_id}/messages",
    response_model=list[ChatMessageResponse],
    dependencies=[th_access],
)
async def list_chat_messages(
    chat_id: str,
    limit: int | None = Query(default=None, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChatMessageResponse]:
    await th_service.get_chat_or_404(db, chat_id, user_id=user.id)
    messages = await th_service.list_messages(db, chat_id, limit=limit)
    return [ChatMessageResponse.model_validate(m) for m in messages]


@router.post(
    "/chats/{chat_id}/messages",
    response_model=ChatMessageResponse,
    dependencies=[th_access],
)
async def send_chat_message(
    chat_id: str,
    payload: ChatMessageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    msg = await th_service.send_message(
        db, chat_id, user.id, payload.content, agent_id=payload.agent_id
    )
    return ChatMessageResponse.model_validate(msg)


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


@router.post(
    "/chats/{chat_id}/messages/stream",
    dependencies=[th_access],
)
async def stream_chat_message(
    chat_id: str,
    payload: ChatMessageCreate,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    async def _generator() -> AsyncIterator[bytes]:
        async with AsyncSessionLocal() as session:
            try:
                async for chunk in th_service.stream_message(
                    session,
                    chat_id,
                    user.id,
                    payload.content,
                    agent_id=payload.agent_id,
                ):
                    yield _sse("chunk", {"text": chunk})
                yield _sse("done", {})
            except Exception:
                logger.exception("SSE streaming failed for chat %s", chat_id)
                yield _sse("error", {"message": "Streaming failed. Please try again."})

    return StreamingResponse(
        _generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
