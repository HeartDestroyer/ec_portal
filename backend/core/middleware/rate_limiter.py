# core/middleware/rate_limiter.py

from fastapi import Request, HTTPException, status, FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from core.extensions.redis import redis_client, Redis
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
        redis: Redis | None = redis_client.get_client()
        if not redis:
            logger.error("Rate Limiter: Redis client не инициализирован")
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

        except Exception as err:
                logger.error(f"Rate Limiter: Ошибка при работе с Redis: {err}", exc_info=True)
                pass

        response = await call_next(request)
        return response
