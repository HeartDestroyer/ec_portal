# backend/core/services/base_service.py - Базовый сервис с общей логикой

from abc import ABC
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import Optional

from core.extensions.logger import logger

class BaseService(ABC):
    """
    Базовый сервис с общей логикой\n
    `db` - Сессия базы данных\n
    `redis` - Redis клиент (опционально)\n
    `logger` - Логгер для текущего класса
    """
    
    def __init__(self, db: AsyncSession, redis: Optional[Redis] = None):
        self.db = db
        self.redis = redis
        self.logger = logger.getChild(self.__class__.__name__)

    async def commit_transaction(self) -> None:
        """
        Подтверждение транзакции
        """
        await self.db.commit()

    async def rollback_transaction(self) -> None:
        """
        Откат транзакции
        """
        await self.db.rollback()

    def log_info(self, message: str, **kwargs) -> None:
        """
        Логирование информации с контекстом сервиса\n
        `message` - Сообщение для логирования\n
        `**kwargs` - Дополнительные аргументы для логирования
        """
        self.logger.info(message, extra=kwargs)

    def log_error(self, message: str, **kwargs) -> None:
        """
        Логирование ошибок с контекстом сервиса\n
        `message` - Сообщение для логирования\n
        `**kwargs` - Дополнительные аргументы для логирования
        """
        self.logger.error(message, extra=kwargs)

    def log_warning(self, message: str, **kwargs) -> None:
        """
        Логирование предупреждений с контекстом сервиса\n
        `message` - Сообщение для логирования\n
        `**kwargs` - Дополнительные аргументы для логирования
        """
        self.logger.warning(message, extra=kwargs)

    def log_debug(self, message: str, **kwargs) -> None:
        """
        Логирование отладочной информации с контекстом сервиса\n
        `message` - Сообщение для логирования\n
        `**kwargs` - Дополнительные аргументы для логирования
        """
        self.logger.debug(message, extra=kwargs)
