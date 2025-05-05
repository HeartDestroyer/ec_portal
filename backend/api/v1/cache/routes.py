
from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from api.v1.dependencies import get_redis
from core.extensions.logger import logger

cache_router = APIRouter(prefix="/api/v1/cache", tags=["Управление кэшем"])

@cache_router.post(
    "/clear",
    summary="Очистка кэша (ключи с префиксом cache:)"
)
async def clear_cache(
    redis: Redis = Depends(get_redis)
):
    """
    Очищает только кэш (ключи с префиксом cache:)
    """
    try:
        keys_cache = await redis.keys("cache:*") # Получение ключей с префиксом cache:
        keys_all = await redis.keys('*') # Получение всех ключей

        if keys_cache:
            await redis.delete(*keys_cache)

        return {"message": f"Кэш успешно очищен, удалено {len(keys_cache)} ключей из {len(keys_all)}"}
    except Exception as err:
        logger.error(f"Ошибка при очистке кэша: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при очистке кэша"
        )
