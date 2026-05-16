import sys
from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.api.translation_helper import chats as chats_router
from app.db.models.translation_helper import (
    ChatMessageRole,
    THChatMessage,
)
from app.services.translation_helper.stream_message import stream_message
from tests.baker import make_th_agent_prompt, make_th_chat, make_user

_STREAM_MOD = sys.modules["app.services.translation_helper.stream_message"]


def _patch_stream(monkeypatch, chunks: list[str]) -> None:
    async def fake_stream(*, system_prompt, contents, settings) -> AsyncIterator[str]:
        for c in chunks:
            yield c

    monkeypatch.setattr(_STREAM_MOD, "_stream_chunks", fake_stream)


@pytest.mark.asyncio
async def test_stream_message_yields_chunks_in_order(monkeypatch, db_session) -> None:
    user = await make_user(db_session, email="th_stream_a@test.com")
    chat = await make_th_chat(db_session, user.id)
    await make_th_agent_prompt(db_session, agent_id="storyteller", prompt="P")

    _patch_stream(monkeypatch, ["Hello", " ", "world"])

    out: list[str] = []
    async for piece in stream_message(db_session, chat.id, user.id, "hi"):
        out.append(piece)
    assert out == ["Hello", " ", "world"]


@pytest.mark.asyncio
async def test_stream_message_persists_concatenated_text(monkeypatch, db_session) -> None:
    user = await make_user(db_session, email="th_stream_b@test.com")
    chat = await make_th_chat(db_session, user.id)
    await make_th_agent_prompt(db_session, agent_id="storyteller", prompt="P")

    _patch_stream(monkeypatch, ["A", "B", "C"])

    async for _ in stream_message(db_session, chat.id, user.id, "hi"):
        pass

    rows = (
        (
            await db_session.execute(
                select(THChatMessage)
                .where(THChatMessage.chat_id == chat.id)
                .order_by(THChatMessage.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    assert [r.role for r in rows] == [ChatMessageRole.USER, ChatMessageRole.ASSISTANT]
    assert rows[0].content == "hi"
    assert rows[1].content == "ABC"


@pytest.mark.asyncio
async def test_stream_chat_message_error_event_does_not_leak_exception(monkeypatch) -> None:
    """Pins B-5: SSE error events must show a generic message, not the raw exception."""
    secret = "SUPER_SECRET_INTERNAL_DETAIL_xyz123"

    async def boom(*args, **kwargs):
        raise RuntimeError(secret)
        yield  # pragma: no cover — make this an async generator

    fake_service = SimpleNamespace(stream_message=boom)
    monkeypatch.setattr(chats_router, "th_service", fake_service)

    class _FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(chats_router, "AsyncSessionLocal", lambda: _FakeSession())

    fake_user = SimpleNamespace(id="user-1")
    payload = SimpleNamespace(content="hi", agent_id=None)

    response = await chats_router.stream_chat_message(
        chat_id="chat-1",
        payload=payload,
        user=fake_user,
    )

    body = b"".join([chunk async for chunk in response.body_iterator])
    decoded = body.decode("utf-8")
    assert "Streaming failed" in decoded
    assert secret not in decoded
    assert "RuntimeError" not in decoded
