# backend/core/extensions/redis.py

import redis.asyncio as redis
from redis.asyncio import Redis
from typing import Optional
from core.config.config import settings
from core.extensions.logger import logger

# Управление Redis
class RedisClient:
    """
    Класс для управления Redis
    """
    def __init__(self):
        self._redis: Optional[Redis] = None

    # Инициализация асинхронного клиента Redis
    async def init_redis(self) -> None:
        """
        Инициализирует пул соединений Redis
        """
        if self._redis is None:            
            self._redis = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True # Автоматически декодировать ответы в строки
            )
            try:
                await self._redis.ping()
                logger.info("Redis client инициализирован")
            except Exception:
                self._redis = None
                logger.error("Redis client не инициализирован")

    # Закрытие соединения с Redis
    async def close_redis(self) -> None:
        """
        Закрывает пул соединений Redis
        """
        if self._redis:
            await self._redis.close()
            self._redis = None

    # Получение активного клиента Redis
    def get_client(self) -> Optional[Redis]:
        """
        Возвращает активный клиент Redis
        """
        if self._redis is None:
            logger.warning("Внимание: Клиент Redis был доступен до инициализации")
        return self._redis

    # Методы-обертки для удобства
    async def set(self, key: str, value: str, expire_seconds: Optional[int] = None) -> Optional[bool]:
        """
        Устанавливает значение в Redis
        """
        if not self._redis: return None
        return await self._redis.set(key, value, ex=expire_seconds)

    # Получение значения из Redis
    async def get(self, key: str) -> Optional[str]:
        """
        Получает значение из Redis
        """
        if not self._redis: return None
        return await self._redis.get(key)

    # Удаление значения из Redis
    async def delete(self, key: str) -> Optional[int]:
        """
        Удаляет значение из Redis
        """
        if not self._redis: return None
        return await self._redis.delete(key)

# Глобальный экземпляр клиента Redis
redis_client = RedisClient()

# Зависимость FastAPI для получения клиента Redis
async def get_redis() -> Optional[Redis]:
    client = redis_client.get_client()
    if client is None:
        raise RuntimeError("Клиент Redis не инициализирован")
    return client
