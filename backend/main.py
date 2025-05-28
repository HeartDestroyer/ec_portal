from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from typing import Callable, List, Any
import time
import pkg_resources
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

from core.config.config import settings
from models.base import Base
from core.extensions.database import engine
from core.extensions.redis import redis_client
from core.websocket.websocket import websocket_manager
from core.extensions.logger import logger
from core.middleware.rate_limiter import RateLimitMiddleware
from core.middleware.security import SecurityMiddleware
from core.middleware.metrics import PrometheusMiddleware


# Wrapper для асинхронных итераторов, обеспечивающий правильное закрытие
class AsyncIteratorWrapper:
    """
    Wrapper для асинхронных итераторов, обеспечивающий правильное закрытие
    """
    def __init__(self, obj: Any) -> None:
        self._it = obj
        self._close_callbacks: List[Callable] = []

    async def __aiter__(self) -> Any:
        try:
            async for item in self._it:
                yield item
        finally:
            for callback in self._close_callbacks:
                await callback()

    def add_callback(self, callback: Callable) -> None:
        self._close_callbacks.append(callback)

# Middleware для измерения времени выполнения запросов
class TimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для измерения времени выполнения запросов
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        response.headers["X-Process-Time"] = str(duration)
        return response

# Проверка совместимости версий библиотек
async def check_dependencies() -> None:
    """
    Проверка совместимости версий библиотек
    """
    logger.info("Проверка совместимости версий библиотек...")
    
    # Необходимые зависимости и их минимальные версии
    required_dependencies = {
        "fastapi": "0.109.1",
        "pydantic": "2.11.3",
        "sqlalchemy": "2.0.25",
        "redis": "4.6.0",
        "uvicorn": "0.27.0",
        "python-jose": "3.3.0",
        "pyotp": "2.8.0",
        "websockets": "15.0.1"
    }
    
    try:
        installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
        
        for package, min_version in required_dependencies.items():
            if package not in installed_packages:
                logger.warning(f"Библиотека {package} не установлена")
                continue
                
            installed_version = installed_packages[package]
            installed_parts = [int(part) for part in installed_version.split(".")[:3]]
            min_parts = [int(part) for part in min_version.split(".")[:3]]
            
            if installed_parts < min_parts:
                logger.warning(
                    f"Установлена устаревшая версия {package}: {installed_version}. "
                    f"Рекомендуется использовать не ниже {min_version}"
                )
                
        # Проверка совместимости Pydantic и FastAPI
        if "pydantic" in installed_packages and "fastapi" in installed_packages:
            pydantic_version = installed_packages["pydantic"]
            fastapi_version = installed_packages["fastapi"]
            
            pydantic_major = int(pydantic_version.split(".")[0])
            fastapi_major = int(fastapi_version.split(".")[1])
            
            if pydantic_major >= 2 and fastapi_major < 109:
                logger.warning(
                    f"Обнаружена возможная проблема совместимости: "
                    f"Pydantic v{pydantic_version} и FastAPI v{fastapi_version}. "
                    f"Рекомендуется использовать FastAPI >=0.109.1 с Pydantic v2.11.3"
                )
                
        logger.info("Проверка зависимостей завершена")
    except Exception as err:
        logger.error(f"Ошибка при проверке зависимостей: {err}")

# Управление жизненным циклом приложения
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

        await check_dependencies()
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


# Инициализация сервисов приложения
async def initialize_services() -> None:
    """
    Инициализация сервисов приложения
    """
    await _initialize_redis()
    await _initialize_database()
    await _initialize_cache()
    # await _initialize_websocket()

async def _initialize_redis() -> None:
    """
    Инициализация Redis
    """
    await redis_client.init_redis()
    
    if not redis_client.get_client():
        raise RuntimeError("Redis не удалось инициализировать")
    
async def _initialize_database() -> None:
    """
    Инициализация базы данных
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as err:
        logger.error(f"Неожиданная ошибка при инициализации базы данных: {err}")
        raise

async def _initialize_cache() -> None:
    """
    Инициализация FastAPI Cache
    """
    try:
        redis = redis_client.get_client()
        FastAPICache.init(RedisBackend(redis), prefix="cache")
    except Exception as err:
        logger.error(f"Неожиданная ошибка при инициализации FastAPI Cache: {err}")
        raise

async def _initialize_websocket() -> None:
    """
    Инициализация WebSocket менеджера
    """
    try:
        await websocket_manager.initialize()
        logger.info("WebSocket менеджер инициализирован")
    except Exception as err:
        logger.error(f"Неожиданная ошибка при инициализации WebSocket менеджера: {err}")
        raise


# Очистка ресурсов при завершении работы
async def cleanup_services() -> None:
    """
    Очистка ресурсов при завершении работы
    """
    # await _cleanup_websocket()
    await _cleanup_cache()
    await _cleanup_redis()
    await _cleanup_database()

async def _cleanup_redis() -> None:
    """
    Очистка Redis соединения
    """
    try:
        if redis_client:
            await redis_client.close_redis()
    except Exception as err:
        logger.error(f"Неожиданная ошибка при закрытии Redis: {err}")
    
async def _cleanup_database() -> None:
    """
    Очистка соединения с базой данных
    """
    try:
        await engine.dispose()
    except Exception as err:
        logger.error(f"Неожиданная ошибка при закрытии соединения с базой данных: {err}")

async def _cleanup_cache() -> None:
    """
    Очистка FastAPI Cache
    """
    try:
        backend = FastAPICache.get_backend()
        if backend is not None:
            await backend.clear("cache")
    except RuntimeError as err:
        pass
    except Exception as err:
        logger.error(f"Неожиданная ошибка при очистке кэша: {err}")

async def _cleanup_websocket() -> None:
    """
    Очистка WebSocket менеджера
    """
    try:
        if websocket_manager:
            await websocket_manager.stop_redis_listener()
            # Отключаем всех клиентов
            for connection_id in list(websocket_manager.connections.keys()):
                connection_info = websocket_manager.connections[connection_id]
                try:
                    await websocket_manager.disconnect(connection_info.websocket, "server_shutdown")
                except Exception as disconnect_err:
                    logger.warning(f"Ошибка при отключении {connection_id}: {disconnect_err}")
            websocket_manager = None
            logger.info("WebSocket менеджер успешно остановлен")

    except Exception as err:
        logger.error(f"Неожиданная ошибка при очистке WebSocket менеджера: {err}")


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

    _configure_cors(app)
    _configure_middleware(app)
    register_exception_handlers(app)
    register_routers(app)

    return app

def _configure_cors(app: FastAPI) -> None:
    """
    Настройка CORS
    """
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        )
        logger.info(f"CORS включен для источников: {settings.CORS_ORIGINS}")

def _configure_middleware(app: FastAPI) -> None:
    """
    Настройка middleware
    """
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(PrometheusMiddleware)
    app.add_middleware(TimingMiddleware)


# Регистрация обработчиков ошибок
def register_exception_handlers(app: FastAPI) -> None:
    """
    Регистрация обработчиков ошибок
    """
    # Обработчик для валидации данных
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"message": error["msg"][13:] if error["msg"].startswith("Value error, ") else error["msg"]}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"errors": errors}
        )

    # Обработчик для HTTPException
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        logger.warning(f"HTTP-исключение: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": exc.detail},
            headers=exc.headers,
        )

    # Обработчик для всех остальных исключений
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(f"Необработанное исключение: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Внутренняя ошибка сервера"},
        )

# Регистрация маршрутов приложения
def register_routers(app: FastAPI) -> None:
    """
    Регистрация маршрутов приложения
    """
    from api.v1.routes import api_router
    app.include_router(api_router, prefix=settings.API_PREFIX)

app = create_application()

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
