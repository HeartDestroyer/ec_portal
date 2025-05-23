import redis.asyncio as redis
from redis.asyncio import Redis
from typing import Optional

from core.config.config import settings
from core.extensions.logger import logger


class RedisClient:
    """    
    Методы класса:
    - init_redis() - Инициализация асинхронного клиента Redis
    - close_redis() - Закрытие пула соединений Redis
    - get_client() - Получение активного клиента Redis
    - get_client_with_retry() - Получение активного клиента Redis с повторными попытками подключения
    - set() - Установка значения в Redis (без атомарности)
    - atomic_set_token() - Установка значения в Redis атомарно (Защита от дублирования токенов)
    - get() - Получение значения из Redis
    - delete() - Удаление значения из Redis

    Функции класса:
    - get_redis() - Получение активного клиента Redis
    """
    def __init__(self):
        self._redis: Optional[Redis] = None
        self.redis_url = settings.REDIS_URL
        self.redis_ssl = settings.REDIS_SSL
        self.redis_max_connections = settings.REDIS_MAX_CONNECTIONS
        self.redis_timeout = settings.REDIS_TIMEOUT
        self.atomic_token_set_script = """
            redis.call('DEL', KEYS[1])
            redis.call('SET', KEYS[1], ARGV[1])
            redis.call('EXPIRE', KEYS[1], ARGV[2])
            return 1
        """

    async def init_redis(self) -> None:
        """
        Инициализация асинхронного клиента Redis\n
        Инициализирует пул соединений Redis
        """
        if not self.redis_url:
            logger.error("Redis URL не указан в настройках")
            return

        if self._redis is None:            
            try:
                connection_params = {
                    "encoding": "utf-8",
                    "decode_responses": False, # True возвращает сразу строку, False возвращает bytes
                    "socket_timeout": self.redis_timeout,
                    "socket_connect_timeout": self.redis_timeout,
                    "retry_on_timeout": True,
                    "max_connections": self.redis_max_connections
                }
                
                if self.redis_ssl:
                    connection_params.update({
                        "ssl_cert_reqs": None,
                        "ssl": self.redis_ssl
                    })
                
                self._redis = await redis.from_url(
                    self.redis_url,
                    **connection_params
                )
                await self._redis.ping()
                logger.info("Redis успешно инициализирован")

            except redis.ConnectionError as err:
                logger.error(f"Ошибка подключения к Redis: {err}")
                self._redis = None
            except Exception as err:
                logger.error(f"Неожиданная ошибка при инициализации Redis: {err}")
                self._redis = None

    async def close_redis(self) -> None:
        """
        Закрывает пула соединений Redis
        """
        if self._redis:
            await self._redis.close()
            self._redis = None

    def get_client(self) -> Optional[Redis]:
        """
        Получает активный клиент Redis
        """
        if self._redis is None:
            logger.warning("Внимание: Клиент Redis был доступен до инициализации")
        return self._redis

    async def get_client_with_retry(self, max_attempts: int = 3) -> Optional[Redis]:
        """
        Получает активный клиент Redis с повторными попытками подключения\n
        `max_attempts` - Максимальное количество попыток подключения\n
        Возвращает клиент Redis или None
        """
        for attempt in range(max_attempts):
            client = self.get_client()
            if client is not None:
                try:
                    # Проверяем соединение
                    await client.ping()
                    return client
                except Exception as err:
                    logger.warning(f"Ошибка при проверке подключения к Redis (попытка {attempt+1}/{max_attempts}): {err}")
                    # Пытаемся переинициализировать соединение
                    await self.close_redis()
                    await self.init_redis()
                    continue
            else:
                logger.warning(f"Клиент Redis недоступен (попытка {attempt+1}/{max_attempts})")
                await self.init_redis()
                
        logger.error(f"Не удалось подключиться к Redis после {max_attempts} попыток")
        return None

    async def set(self, key: str, value: str, expire_seconds: Optional[int] = None) -> Optional[bool]:
        """
        Устанавливает значение в Redis (без атомарности)\n
        `key` - Ключ\n
        `value` - Значение\n
        `expire_seconds` - Время жизни ключа в секундах
        """
        if not self._redis: return None
        return await self._redis.set(key, value, ex=expire_seconds)

    async def atomic_set_token(self, key: str, value: str, expire_seconds: Optional[int] = None) -> bool:
        """
        Устанавливает значение в Redis атомарно (Защита от дублирования токенов)\n
        `key` - Ключ\n
        `value` - Значение\n
        `expire_seconds` - Время жизни ключа в секундах
        """
        if not self._redis: return False
        return await self._redis.eval(self.atomic_token_set_script, 1, key, value, expire_seconds)

    async def get(self, key: str) -> Optional[str]:
        """
        Получает значение из Redis\n
        `key` - Ключ
        """
        if not self._redis: return None
        return await self._redis.get(key)

    async def delete(self, key: str) -> Optional[int]:
        """
        Удаляет значение из Redis\n
        `key` - Ключ
        """
        if not self._redis: return None
        return await self._redis.delete(key)

redis_client = RedisClient()

async def get_redis() -> Optional[Redis]:
    """
    Получает активный клиент Redis
    """
    client = redis_client.get_client()
    if client is None:
        raise RuntimeError("Клиент Redis не инициализирован")
    return client
