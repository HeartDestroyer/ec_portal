import pytest
from fastapi.testclient import TestClient
import asyncio
from typing import AsyncGenerator, Generator

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_app():
    from main import create_application
    app = create_application()
    await app.router.startup()
    yield app
    await app.router.shutdown()

@pytest.fixture(scope="session")
async def test_client(test_app):
    async with TestClient(test_app) as client:
        yield client

@pytest.fixture
async def test_db() -> AsyncGenerator:
    from core.extensions.database import get_db
    async for session in get_db():
        yield session