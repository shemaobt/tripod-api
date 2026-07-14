from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport


@pytest.fixture()
async def client(db_session):
    """ASGI client montando SÓ o router da plataforma.

    Roda a cadeia de auth REAL (`get_current_user`) — é ela que precisa ser provada:
    a plataforma não tem app-key, então o endpoint atende qualquer usuário autenticado,
    de qualquer app, e um anônimo tem de ser barrado.
    """
    from fastapi import FastAPI

    from app.api.platform import router as platform_router
    from app.core.database import get_db
    from app.core.exceptions import register_exception_handlers

    test_app = FastAPI()
    test_app.include_router(platform_router, prefix="/api/platform")
    register_exception_handlers(test_app)

    async def _get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = _get_db
    transport = ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def auth_header(db_session, user) -> dict[str, str]:
    """Um bearer token real para `user` (decodificado pela dependência de auth)."""
    from app.services.auth.issue_tokens import issue_tokens

    access, _refresh = await issue_tokens(db_session, user)
    return {"Authorization": f"Bearer {access}"}
