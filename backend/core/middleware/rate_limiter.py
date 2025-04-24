# core/middleware/rate_limiter.py

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from core.extensions.redis import redis_client
from core.config.config import settings

# Middleware для ограничения количества запросов на API
class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware для ограничения количества запросов на API
    """
    def __init__(self):
        self.time_rate_limiter = settings.TIME_RATE_LIMITER
        self.size_rate_limiter = settings.SIZE_RATE_LIMITER

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        key = f"rate_limit:{client_ip}"
        
        # Проверка лимита запросов
        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, self.time_rate_limiter)
            
        if current > self.size_rate_limiter:
            raise HTTPException(status_code=429, detail="Слишком много запросов")
            
        response = await call_next(request)
        return response
