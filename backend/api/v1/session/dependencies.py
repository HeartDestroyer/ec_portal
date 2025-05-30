# backend/api/v1/session/dependencies.py - Зависимости для сессий

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from api.v1.dependencies import get_db, get_redis, jwt_service, JWTService
from core.interfaces.session.session_repositories import SessionRepositoryInterface
from core.interfaces.session.session_services import SessionServiceInterface
from repositories.session_repository import SessionRepository
from api.v1.session.services.session_service import SessionService

async def get_session_repository(
    db: AsyncSession = Depends(get_db)
) -> SessionRepositoryInterface:
    """
    Создает экземпляр репозитория сессий\n
    `db` - Сессия базы данных\n
    Возвращает экземпляр репозитория сессий
    """
    return SessionRepository(db)

def create_session_service(
    db: AsyncSession = Depends(get_db),
    jwt_handler: JWTService = Depends(jwt_service),
    redis: Redis = Depends(get_redis)
) -> SessionServiceInterface:
    """
    Создает экземпляр сервиса сессий
    """
    return SessionService(db, jwt_handler, redis)
