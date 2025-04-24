# backend/core/middleware/metrics.py

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, start_http_server, REGISTRY
import time
from core.config.config import settings
from core.extensions.logger import logger
import os

# --- Prometheus метрики ---
# Счетчик HTTP запросов
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests processed",
    ["method", "path", "status_code"]
)
# Гистограмма времени выполнения запросов
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"]
)
# Счетчик активных запросов (Gauge пока не используется, но можно добавить)
# IN_PROGRESS_REQUESTS = Gauge(
#     "http_requests_in_progress_total",
#     "Total number of HTTP requests currently in progress",
#     ["method", "path"]
# )

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware для сбора метрик Prometheus
    """
    def __init__(self, app, app_name="fastapi_app"):
        super().__init__(app)
        self.app_name = app_name
        # Добавляем метки по умолчанию, например, имя приложения
        self._register_metric_if_not_exists(REQUEST_COUNT)
        self._register_metric_if_not_exists(REQUEST_LATENCY)

    async def dispatch(self, request: Request, call_next):
        method = request.method
        path = request.url.path

        # Заменяем ID в пути на плейсхолдер для агрегации
        # Пример: /users/123 -> /users/{user_id}
        # Добавьте свои правила, если нужно
        if path.startswith(f"{settings.API_PREFIX}/users/") and path.split('/')[-1].isdigit():
            path = f"{settings.API_PREFIX}/users/{{user_id}}"
        elif path.startswith(f"{settings.API_PREFIX}/auth/"): # Группируем пути авторизации
             path = f"{settings.API_PREFIX}/auth/{{endpoint}}"


        # IN_PROGRESS_REQUESTS.labels(method=method, path=path).inc()
        start_time = time.time()
        status_code = 500 # По умолчанию - ошибка сервера

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as e:
            # Логируем исключение, которое не было перехвачено обработчиками FastAPI
            logger.error(f"Unhandled exception in PrometheusMiddleware: {e}", exc_info=True)
            raise e # Передаем исключение дальше для обработки FastAPI
        finally:
            latency = time.time() - start_time
            # IN_PROGRESS_REQUESTS.labels(method=method, path=path).dec()
            REQUEST_LATENCY.labels(method=method, path=path).observe(latency)
            REQUEST_COUNT.labels(method=method, path=path, status_code=status_code).inc()

    # Регистрация метрик, если они еще не зарегистрированы
    def _register_metric_if_not_exists(self, metric):
            """
            Регистрирует метрику, если она еще не зарегистрирована
            :param metric: метрика для регистрации
            """
            # Получаем имена метрик, связанных с этим коллектором (если он уже есть)
            registered_names = REGISTRY._collector_to_names.get(metric)

            # Если коллектор еще не зарегистрирован ИЛИ
            # если коллектор зарегистрирован, но имя метрики отличается (маловероятно, но для полноты)
            if registered_names is None or metric._name not in registered_names:
                try:
                    REGISTRY.register(metric)
                    # logger.debug(f"Метрика {metric._name} успешно зарегистрирована.")
                except ValueError:
                    # Эта ошибка может возникнуть, если метрика с таким именем
                    # уже зарегистрирована другим экземпляром коллектора (или в гонке потоков).
                    # В большинстве случаев это означает, что она уже есть, и мы можем продолжить.
                    # logger.warning(f"Метрика {metric._name} уже была зарегистрирована.")
                    pass 

# Функция для запуска сервера метрик Prometheus
def start_metrics_server():
    """
    Запускает HTTP сервер для предоставления метрик Prometheus
    """
    if settings.ENABLE_METRICS:
        try:
            # Запускаем сервер в отдельном процессе, если это основной процесс uvicorn
            # (чтобы избежать блокировки и проблем с reload)
            # Проверяем, запущен ли uvicorn с reload
            is_reload = any("uvicorn.workers.UvicornWorker" in str(s) for s in os.sys.argv)

            # Запускаем только если метрики включены и это не дочерний процесс reload
            if not is_reload or os.getenv("PROMETHEUS_MULTIPROC_DIR"):
                 # Или если используется multi-process mode для Gunicorn/Uvicorn workers
                 # (требует настройки PROMETHEUS_MULTIPROC_DIR)
                start_http_server(settings.METRICS_PORT)
                logger.info(f"Prometheus metrics server started on port {settings.METRICS_PORT}")
        except OSError as e:
             logger.warning(f"Could not start Prometheus metrics server on port {settings.METRICS_PORT}: {e}. Port likely in use.")
        except Exception as e:
             logger.error(f"Failed to start Prometheus metrics server: {e}", exc_info=True)

# Вызываем запуск сервера метрик при импорте модуля
# (но с проверками, чтобы избежать запуска в дочерних процессах reload)
# Более надежный способ - запускать его в lifespan или отдельном скрипте
# start_metrics_server()