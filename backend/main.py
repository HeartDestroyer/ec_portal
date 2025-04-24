# main.py
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
import logging.config
from typing import Callable
import time
import asyncio
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

# Конфигурация и расширения
from core.config.config import settings
from core.extensions.database import engine, SessionLocal
from core.extensions.redis import redis_client
from core.extensions.logger import Logger, logger
from core.models.base import Base
from core.middleware.rate_limiter import RateLimitMiddleware
from core.middleware.security import SecurityMiddleware
from core.middleware.metrics import PrometheusMiddleware

# Метрики
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests')
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')

# Wrapper для асинхронных итераторов 
class AsyncIteratorWrapper:
    """
    Wrapper для асинхронных итераторов, обеспечивающий правильное закрытие
    """
    def __init__(self, obj):
        self._it = obj
        self._close_callbacks = []

    async def __aiter__(self):
        try:
            async for item in self._it:
                yield item
        finally:
            for callback in self._close_callbacks:
                await callback()

    def add_callback(self, callback):
        self._close_callbacks.append(callback)

# Middleware для измерения времени выполнения запросов
class TimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для измерения времени выполнения запросов
    """
    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        
        REQUEST_LATENCY.observe(duration)
        response.headers["X-Process-Time"] = str(duration)
        return response

# Контекстный менеджер для управления ресурсами при старте/остановке приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения
    """
    try:
        logger.info("Запуск приложения...")
        await redis_client.init_redis()

        # Инициализация базы данных
        async with engine.begin() as conn:
            logger.info("Инициализация таблиц базы данных...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Таблицы базы данных инициализированы")

        # Инициализация сервисов
        await initialize_services()

        logger.info("Приложение запущено")
        yield

    except Exception as err:
        logger.error(f"Ошибка при запуске приложения: {err}", exc_info=True)
        raise
    finally:
        # Очистка ресурсов
        logger.info("Закрытие приложения...")
        await cleanup_services()
        await redis_client.close_redis()
        await engine.dispose()
        logger.info("Приложение завершено")

# Инициализация дополнительных сервисов
async def initialize_services():
    """
    Инициализация дополнительных сервисов
    """
    pass

# Очистка ресурсов при завершении работы
async def cleanup_services():
    """
    Очистка ресурсов при завершении работы
    """
    pass

# Создание экземпляра FastAPI
def create_application() -> FastAPI:
    """
    Создание экземпляра FastAPI
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
        docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
        redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    )

    # Настройка CORS
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        )
        logger.info(f"CORS включен для источников: {settings.CORS_ORIGINS}")

    # Добавление middleware
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(PrometheusMiddleware)
    app.add_middleware(TimingMiddleware)

    # Регистрация обработчиков ошибок
    register_exception_handlers(app)

    # Регистрация роутеров
    register_routers(app)

    return app

# Регистрация обработчиков ошибок
def register_exception_handlers(app: FastAPI):
    """
    Регистрация обработчиков ошибок
    """
    # Обработчик для HTTPException
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    # Обработчик для всех остальных исключений
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Внутренняя ошибка сервера"},
        )

# Регистрация роутеров
def register_routers(app: FastAPI):
    """
    Регистрация роутеров
    """
    # Роутеры
    from api.v1.auth.routes import auth_router

    # Регистрация роутеров
    app.include_router(auth_router, prefix=settings.API_PREFIX)

app = create_application()

# --- Запуск через Uvicorn ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        workers=settings.WORKERS_COUNT,
        loop="uvloop",
        limit_concurrency=settings.LIMIT_CONCURRENCY,
        timeout_keep_alive=settings.TIMEOUT_KEEP_ALIVE,
    )
