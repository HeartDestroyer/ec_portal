# backend/api/v1/auth/dependencies.py - Зависимости для аутентификации и регистрации

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from api.v1.dependencies import get_db, get_redis, JWTHandler, EmailManager, SessionManager
from repositories.user_repository import UserRepository
from core.interfaces.auth.auth_repositories import UserRepositoryInterface
from core.interfaces.auth.auth_services import (
    AuthenticationServiceInterface, RegistrationServiceInterface, PasswordServiceInterface, TwoFactorServiceInterface
)
from api.v1.auth.services import (
    AuthenticationService, RegistrationService, PasswordService, TwoFactorService
)

async def get_user_repository(
    db: AsyncSession = Depends(get_db)
) -> UserRepositoryInterface:
    """
    Создает экземпляр репозитория пользователей\n
    `db` - Сессия базы данных\n
    Возвращает экземпляр репозитория пользователей
    """
    return UserRepository(db)

async def create_authentication_service(
    db: AsyncSession = Depends(get_db), 
    redis: Redis = Depends(get_redis),
    user_repository: UserRepositoryInterface = Depends(get_user_repository),
    jwt_handler: JWTHandler = Depends(JWTHandler), 
    session_manager: SessionManager = Depends(SessionManager),
    email_manager: EmailManager = Depends(EmailManager),
) -> AuthenticationServiceInterface:
    """
    Создает экземпляр сервиса аутентификации\n
    `db` - Сессия базы данных\n
    `redis` - Redis\n
    `user_repository` - Репозиторий пользователей\n
    `jwt_handler` - JWTHandler\n
    `session_manager` - SessionManager\n
    `email_manager` - EmailManager\n
    Возвращает экземпляр сервиса аутентификации
    """
    return AuthenticationService(db, redis, user_repository, jwt_handler, session_manager, email_manager)

async def create_registration_service(
    db: AsyncSession = Depends(get_db), 
    redis: Redis = Depends(get_redis),
    user_repository: UserRepositoryInterface = Depends(get_user_repository),
    email_manager: EmailManager = Depends(EmailManager),
    jwt_handler: JWTHandler = Depends(JWTHandler),
) -> RegistrationServiceInterface:
    """
    Создает экземпляр сервиса регистрации\n
    `db` - Сессия базы данных\n
    `redis` - Redis\n
    `user_repository` - Репозиторий пользователей\n
    `email_manager` - EmailManager\n
    `jwt_handler` - JWTHandler\n
    Возвращает экземпляр сервиса регистрации
    """
    return RegistrationService(db, redis, user_repository, email_manager, jwt_handler)

async def create_password_service(
    db: AsyncSession = Depends(get_db), 
    redis: Redis = Depends(get_redis),
    user_repository: UserRepositoryInterface = Depends(get_user_repository),
    email_manager: EmailManager = Depends(EmailManager),
    jwt_handler: JWTHandler = Depends(JWTHandler),
    session_manager: SessionManager = Depends(SessionManager),
) -> PasswordServiceInterface:
    """
    Создает экземпляр сервиса работы с паролями\n
    `db` - Сессия базы данных\n
    `redis` - Redis\n
    `user_repository` - Репозиторий пользователей\n
    `email_manager` - EmailManager\n
    `jwt_handler` - JWTHandler\n
    `session_manager` - SessionManager\n
    Возвращает экземпляр сервиса работы с паролями
    """
    return PasswordService(db, redis, user_repository, email_manager, jwt_handler, session_manager)

async def create_two_factor_service(
    db: AsyncSession = Depends(get_db), 
    redis: Redis = Depends(get_redis),
) -> TwoFactorServiceInterface:
    """
    Создает экземпляр сервиса 2FA\n
    `db` - Сессия базы данных\n
    `redis` - Redis\n
    Возвращает экземпляр сервиса 2FA
    """
    return TwoFactorService(db, redis)
