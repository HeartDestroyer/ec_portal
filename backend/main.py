# main.py
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from typing import Callable
import time
from starlette.middleware.base import BaseHTTPMiddleware

# Конфигурация и расширения
from core.config.config import settings
from core.extensions.database import engine
from core.extensions.redis import redis_client
from core.extensions.logger import logger
from core.models.base import Base
from core.middleware.rate_limiter import RateLimitMiddleware
from core.middleware.security import SecurityMiddleware
from core.middleware.metrics import PrometheusMiddleware

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

        if not settings.REDIS_URL:
            logger.error("REDIS_URL не настроен в переменных окружения")
            raise ValueError("REDIS_URL не настроен")

        await initialize_services()

        logger.info("Приложение запущено")
        yield

    except Exception as err:
        logger.error(f"Ошибка при запуске приложения: {err}", exc_info=True)
        raise
    finally:
        logger.info("Закрытие приложения...")
        await cleanup_services()
        
        logger.info("Приложение завершено")

# Инициализация сервисов
async def initialize_services():
    """
    Инициализация сервисов
    """
    # Инициализация Redis
    logger.info("Инициализация Redis...")
    await redis_client.init_redis()
    
    # Проверяем, что Redis действительно инициализирован
    if not redis_client.get_client():
        logger.error("Redis не удалось инициализировать")
        raise RuntimeError("Redis не удалось инициализировать")
    
    logger.info("Redis инициализирован успешно")

    # Инициализация базы данных
    try:
        logger.info("Инициализация базы данных...")
        async with engine.begin() as conn:
            logger.info("Инициализация таблиц базы данных...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Таблицы базы данных инициализированы")
    except Exception as err:
        logger.error(f"Ошибка при инициализации базы данных: {err}", exc_info=True)
        raise

# Очистка ресурсов при завершении работы
async def cleanup_services():
    """
    Очистка ресурсов при завершении работы
    """
    try:
        if redis_client:
            logger.info("Закрытие соединения с Redis...")
            await redis_client.close_redis()
            logger.info("Соединение с Redis закрыто")
    except Exception as err:
        logger.error(f"Ошибка при закрытии Redis: {err}", exc_info=True)
    
    try:
        logger.info("Закрытие соединения с базой данных...")
        await engine.dispose()
        logger.info("Соединение с базой данных закрыто")
    except Exception as err:
        logger.error(f"Ошибка при закрытии соединения с базой данных: {err}", exc_info=True)

# Создание экземпляра FastAPI
def create_application() -> FastAPI:
    """
    Создание экземпляра FastAPI
    """
    # Настройка FastAPI
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

    register_exception_handlers(app)
    register_routers(app)

    return app

# Регистрация обработчиков ошибок
def register_exception_handlers(app: FastAPI):
    """
    Регистрация обработчиков ошибок
    """
    # Обработчик для валидации данных
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            message = error["msg"]
            if message.startswith("Value error, "):
                message = message[13:]
            errors.append({
                "message": message
            })
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"errors": errors}
        )

    # Обработчик для HTTPException
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(f"HTTP-исключение: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": exc.detail},
            headers=exc.headers,
        )

    # Обработчик для всех остальных исключений
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"Необработанное исключение: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Внутренняя ошибка сервера"},
        )

# Регистрация роутеров
def register_routers(app: FastAPI):
    """
    Регистрация роутеров
    """
    from api.v1.routes import api_router
    app.include_router(api_router, prefix=settings.API_PREFIX)

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
