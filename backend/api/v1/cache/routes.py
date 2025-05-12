from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from api.v1.dependencies import get_redis
from core.extensions.logger import logger
from typing import Dict, Any

cache_router = APIRouter(prefix="/api/v1/cache", tags=["Управление кэшем"])

# Очистка кэша Redis
@cache_router.post(
    "/clear",
    summary="Очистка кэша Redis"
)
async def clear_cache(
    redis: Redis = Depends(get_redis)
):
    """
    Очищает только ключи с префиксом `cache:`
    """
    try:
        keys_cache = await redis.keys("cache:*") # Получение ключей с префиксом cache:

        if keys_cache:
            await redis.delete(*keys_cache)

        return {"message": f"Кэш успешно очищен, удалено {len(keys_cache)} ключей"}
    except Exception as err:
        logger.error(f"Ошибка при очистке кэша: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при очистке кэша"
        )

# Получение информации о Redis
@cache_router.get(
    "/info",
    summary="Получение информации о Redis"
)
async def get_redis_info(
    redis: Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """
    Возвращает основную информацию о сервере Redis: 
    память, нагрузка, статистика и тд
    """
    try:
        info = await redis.info()
        return {
            "memory": {
                "used_memory_human": f"Использовано памяти: {info.get('used_memory_human', 'Н/Д')}",
                "used_memory_peak_human": f"Использовано памяти (пик): {info.get('used_memory_peak_human', 'Н/Д')}",
                "used_memory_rss_human": f"Использовано памяти (RSS): {info.get('used_memory_rss_human', 'Н/Д')}",
                "mem_fragmentation_ratio": f"Коэффициент фрагментации: {info.get('mem_fragmentation_ratio', 'Н/Д')}",
            },
            "stats": {
                "total_connections_received": f"Всего подключений: {info.get('total_connections_received', 0)}",
                "total_commands_processed": f"Всего команд: {info.get('total_commands_processed', 0)}",
                "instantaneous_ops_per_sec": f"Операций в секунду: {info.get('instantaneous_ops_per_sec', 0)}",
                "rejected_connections": f"Отклоненных подключений: {info.get('rejected_connections', 0)}",
            },
            "server": {
                "redis_version": f"Версия Redis: {info.get('redis_version', 'Н/Д')}",
                "uptime_in_days": f"Время работы (дни): {info.get('uptime_in_days', 0)}",
                "connected_clients": f"Подключенных клиентов: {info.get('connected_clients', 0)}",
                "blocked_clients": f"Блокированных клиентов: {info.get('blocked_clients', 0)}",
            }
        }
    except Exception as err:
        logger.error(f"Ошибка при получении информации о Redis: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении информации о Redis"
        )

# Получение количества ключей в Redis
@cache_router.get(
    "/keys",
    summary="Получение количества ключей в Redis"
)
async def get_redis_keys(
    pattern: str = "*",
    redis: Redis = Depends(get_redis)
) -> Dict[str, int | str]:
    """
    Возвращает количество ключей в Redis по указанному шаблону.
    По умолчанию возвращает количество всех ключей.
    """
    try:
        keys = await redis.keys(pattern)
        total_keys = len(keys)
         
        return {
            "total_keys": total_keys,
            "pattern": pattern,
        }
    except Exception as err:
        logger.error(f"Ошибка при получении количества ключей Redis: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении количества ключей Redis"
        )
