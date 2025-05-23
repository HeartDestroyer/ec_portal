from fastapi import APIRouter, Depends, HTTPException, status, Request
from redis.asyncio import Redis

from .schemas import RedisInfo, RedisKeys
from api.v1.schemas import MessageResponse
from api.v1.dependencies import get_redis, require_admin_roles
from core.extensions.logger import logger

cache_router = APIRouter(prefix="/api/v1/cache", tags=["Управление кэшем"])

# Очистка кэша Redis
@cache_router.post(
    "/clear",
    response_model=MessageResponse,
    summary="Очистка кэша Redis"
)
@require_admin_roles()
async def clear_cache(
    request: Request,
    redis: Redis = Depends(get_redis)
) -> MessageResponse:
    """
    Авторизованный API. Доступ: `Администраторы`\n
    Очищает только ключи с префиксом `cache:`
    """
    try:
        keys_cache = await redis.keys("cache:*")
        if keys_cache:
            await redis.delete(*keys_cache)

        return MessageResponse(message=f"Кэш успешно очищен, удалено {len(keys_cache)} ключей")
    
    except Exception as err:
        logger.error(f"Ошибка при очистке кэша: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при очистке кэша"
        )

# Получение информации о Redis
@cache_router.get(
    "/info",
    response_model=RedisInfo,
    summary="Получение информации о Redis"
)
@require_admin_roles()
async def get_redis_info(
    request: Request,
    redis: Redis = Depends(get_redis)
) -> RedisInfo:
    """
    Авторизованный API. Доступ: `Администраторы`\n
    Возвращает основную информацию о сервере Redis: память, нагрузка, статистика и тд
    """
    try:
        info = await redis.info()
        return RedisInfo(
            memory={
                "used_memory_human": f"Использовано памяти: {info.get('used_memory_human', 'Н/Д')}",
                "used_memory_peak_human": f"Использовано памяти (пик): {info.get('used_memory_peak_human', 'Н/Д')}",
                "used_memory_rss_human": f"Использовано памяти (RSS): {info.get('used_memory_rss_human', 'Н/Д')}",
                "mem_fragmentation_ratio": f"Коэффициент фрагментации: {info.get('mem_fragmentation_ratio', 'Н/Д')}",
            },
            stats={
                "total_connections_received": f"Всего подключений: {info.get('total_connections_received', 0)}",
                "total_commands_processed": f"Всего команд: {info.get('total_commands_processed', 0)}",
                "instantaneous_ops_per_sec": f"Операций в секунду: {info.get('instantaneous_ops_per_sec', 0)}",
                "rejected_connections": f"Отклоненных подключений: {info.get('rejected_connections', 0)}",
            },
            server={
                "redis_version": f"Версия Redis: {info.get('redis_version', 'Н/Д')}",
                "uptime_in_days": f"Время работы (дни): {info.get('uptime_in_days', 0)}",
            },
            clients={
                "connected_clients": f"Подключенных клиентов: {info.get('connected_clients', 0)}",
                "blocked_clients": f"Блокированных клиентов: {info.get('blocked_clients', 0)}",
            },
            persistence={
                "rdb_changes_since_last_save": f"Изменений с последнего сохранения: {info.get('rdb_changes_since_last_save', 0)}",
            }
        )
    
    except Exception as err:
        logger.error(f"Ошибка при получении информации о Redis: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении информации о Redis"
        )

# Получение количества ключей и самих ключей в Redis
@cache_router.get(
    "/keys",
    response_model=RedisKeys,
    summary="Получение количества ключей в Redis"
)
@require_admin_roles()
async def get_redis_keys(
    request: Request,
    pattern: str = "*",
    redis: Redis = Depends(get_redis)
) -> RedisKeys:
    """
    Авторизованный API. Доступ: `Администраторы`\n
    Возвращает количество ключей в Redis по указанному шаблону и сами ключи\n
    По умолчанию возвращает количество всех ключей и все ключи\n
    """
    try:
        keys_raw = await redis.keys(pattern)
        keys = [
            key.decode('utf-8') if isinstance(key, bytes) else key
            for key in keys_raw
        ]

        return RedisKeys(
            total=len(keys),
            pattern=pattern,
            keys=keys
        )
    
    except Exception as err:
        logger.error(f"Ошибка при получении количества ключей Redis: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении количества ключей Redis"
        )
