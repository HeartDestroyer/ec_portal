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

AsyncSessionFactory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Контекстный менеджер для асинхронных сессий\n
    Возвращает сессию
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Зависимость для получения сессии\n
    Возвращает сессию
    """
    async with get_async_session() as session:
        yield session
