# backend/core/extensions/database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from core.config.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQLALCHEMY_ECHO,
    future=True,
    poolclass=QueuePool,
    pool_size=settings.SQLALCHEMY_ENGINE_OPTIONS.get("pool_size", 30),
    max_overflow=settings.SQLALCHEMY_ENGINE_OPTIONS.get("max_overflow", 100),
    pool_timeout=settings.SQLALCHEMY_ENGINE_OPTIONS.get("pool_timeout", 30),
    pool_recycle=settings.SQLALCHEMY_ENGINE_OPTIONS.get("pool_recycle", 1800),
    pool_pre_ping=settings.SQLALCHEMY_ENGINE_OPTIONS.get("pool_pre_ping", True),
)

# Создаем фабрику асинхронных сессий
AsyncSessionFactory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Создаем контекстный менеджер для асинхронных сессий
@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

# Зависимость для получения сессии
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_async_session() as session:
        yield session
