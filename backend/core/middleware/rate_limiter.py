from fastapi import Request, HTTPException, status, FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from core.extensions.redis import redis_client
from core.config.config import settings
from core.extensions.logger import logger

# Middleware для ограничения количества запросов на API
class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware для ограничения количества запросов на API
    """
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.time_rate_limiter = settings.TIME_RATE_LIMITER
        self.size_rate_limiter = settings.SIZE_RATE_LIMITER

    async def dispatch(self, request: Request, call_next):
        try:
            redis = await redis_client.get_client_with_retry()
            if not redis:
                logger.error("Не удалось получить подключение к Redis для ограничения количества запросов")
                return await call_next(request)

            client_ip = request.client.host if request.client else "unknown"
            key = f"rate_limit:{client_ip}:{request.method}:{request.url.path}"
            
            try:
                current = await redis.incr(key)
                if current == 1:
                    await redis.expire(key, self.time_rate_limiter)

                if current > self.size_rate_limiter:
                    ttl = await redis.ttl(key)
                    detail_msg = f"Превышен лимит запросов. Попробуйте снова через {ttl} секунд" if ttl > 0 else "Превышен лимит запросов"
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=detail_msg,
                        headers={"Retry-After": str(ttl)} if ttl > 0 else None
                    )

            except redis.RedisError as err:
                logger.error(f"Ошибка при работе с Redis для ограничения количества запросов: {err}", exc_info=True)
                pass

            response = await call_next(request)
            return response
            
        except Exception as err:
            logger.error(f"Неожиданная ошибка в ограничении количества запросов: {err}", exc_info=True)
            return await call_next(request)
