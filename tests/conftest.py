import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

from app.core.database import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop() -> AsyncGenerator[asyncio.AbstractEventLoop, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    yield engine
    await engine.dispose()


@pytest.fixture()
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession, autoflush=False
    )
    async with session_factory() as session:
        from app.db.models.auth import App

        mm_app = App(
            app_key="meaning-map-generator", name="Meaning Map Generator", is_active=True,
        )
        session.add(mm_app)
        await session.commit()

        yield session
        await session.rollback()
