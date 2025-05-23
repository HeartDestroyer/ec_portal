from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, Gauge, start_http_server, REGISTRY
import time
from core.config.config import settings
from core.extensions.logger import logger
import os

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
# Счетчик активных запросов 
IN_PROGRESS_REQUESTS = Gauge(
    "http_requests_in_progress_total",
    "Total number of HTTP requests currently in progress",
    ["method", "path"]
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware для сбора метрик Prometheus
    Метрики для сбора:
    - общее количество HTTP запросов
    - время выполнения запросов
    - количество активных запросов
    """
    def __init__(self, app, app_name="fastapi_app"):
        super().__init__(app)
        self.app_name = app_name

        self._register_metric_if_not_exists(REQUEST_COUNT)
        self._register_metric_if_not_exists(REQUEST_LATENCY)
        self._register_metric_if_not_exists(IN_PROGRESS_REQUESTS)

    async def dispatch(self, request: Request, call_next):
        method = request.method
        path = request.url.path

        # Счетчик активных запросов
        IN_PROGRESS_REQUESTS.labels(method=method, path=path).inc()

        # Время выполнения запроса
        start_time = time.time()
        status_code = 500 # По умолчанию - ошибка сервера

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as err:
            # Логируем исключение, которое не было перехвачено обработчиками FastAPI
            logger.error(f"Unhandled exception in PrometheusMiddleware: {err}", exc_info=True)
            raise err # Передаем исключение дальше для обработки FastAPI
        finally:
            latency = time.time() - start_time
            # Счетчик активных запросов
            IN_PROGRESS_REQUESTS.labels(method=method, path=path).dec()
            # Гистограмма времени выполнения запроса
            REQUEST_LATENCY.labels(method=method, path=path).observe(latency)
            # Счетчик HTTP запросов
            REQUEST_COUNT.labels(method=method, path=path, status_code=status_code).inc()

    def _register_metric_if_not_exists(self, metric):
        """
        Регистрирует метрику, если она еще не зарегистрирована\n
        `metric` - метрика для регистрации
        """
        # Получаем имена метрик, связанных с этим коллектором (если он уже есть)
        registered_names = REGISTRY._collector_to_names.get(metric)

        # Если коллектор еще не зарегистрирован ИЛИ
        # если коллектор зарегистрирован, но имя метрики отличается
        if registered_names is None or metric._name not in registered_names:
            try:
                REGISTRY.register(metric)
            except ValueError:
                pass 

# Функция для запуска сервера метрик Prometheus
def start_metrics_server():
    """
    Запускает HTTP сервер для предоставления метрик Prometheus\n
    `settings.ENABLE_METRICS` - флаг включения метрик
    """
    if settings.ENABLE_METRICS:
        try:
            is_reload = any("uvicorn.workers.UvicornWorker" in str(s) for s in os.sys.argv)

            # Запускаем только если метрики включены и это не дочерний процесс reload
            if not is_reload or os.getenv("PROMETHEUS_MULTIPROC_DIR"):
                start_http_server(settings.METRICS_PORT)
                logger.info(f"Метрики Prometheus сервер запущен на порту {settings.METRICS_PORT}")

        except OSError as err:
            logger.warning(f"Не удалось запустить сервер метрик Prometheus на порту {settings.METRICS_PORT}: {err}. Порт уже используется")
        except Exception as err:
            logger.error(f"Не удалось запустить сервер метрик Prometheus: {err}", exc_info=True)
