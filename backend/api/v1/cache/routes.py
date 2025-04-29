
from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from api.v1.dependencies import get_redis
from core.extensions.logger import logger

cache_router = APIRouter(prefix="/api/v1/cache", tags=["Управление кэшем"])

@cache_router.post(
    "/clear",
    summary="Очистка кэша"
)
async def clear_cache(
    redis: Redis = Depends(get_redis)
):
    """
    Очищает весь кэш Redis
    """
    try:
        await redis.flushdb()
        return {"message": "Кэш успешно очищен"}
    except Exception as err:
        logger.error(f"Ошибка при очистке кэша: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при очистке кэша"
        )
