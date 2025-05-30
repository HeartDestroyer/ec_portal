from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

from core.config.config import settings

class CustomJsonFormatter(logging.Formatter):
    """
    Кастомный форматтер для логов в JSON формате
    """
    def __init__(self):
        super().__init__()
        self.default_keys = [
            'timestamp', 'level', 'message', 'module',
            'function', 'path', 'line', 'process', 'thread'
        ]

    def format(self, record: logging.LogRecord) -> str:
        """
        Форматирует запись лога в JSON\n
        `record` - Запись лога\n
        Возвращает отформатированную запись в JSON
        """
        log_object: Dict[str, Any] = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'message': str(record.getMessage()),  # Явно преобразуем в строку
            'module': record.module,
            'function': record.funcName,
            'path': record.pathname,
            'line': record.lineno,
            'process': record.process,
            'thread': record.thread
        }

        # Добавляем дополнительные атрибуты из record.__dict__
        for key, value in record.__dict__.items():
            if key not in self.default_keys and not key.startswith('_'):
                try:
                    if isinstance(value, (str, int, float, bool, type(None))):
                        log_object[key] = value
                    elif isinstance(value, (list, tuple, set)):
                        log_object[key] = [str(item) for item in value]
                    elif isinstance(value, dict):
                        log_object[key] = {str(k): str(v) for k, v in value.items()}
                    else:
                        log_object[key] = str(value)
                except Exception:
                    log_object[key] = f"<{type(value).__name__} обьект (несериализуемый)>"

        # Добавляем информацию об исключении, если оно есть
        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            log_object['exception'] = {
                'type': exc_type.__name__ if exc_type else None,
                'message': str(exc_value) if exc_value else None,
                'traceback': self.formatException(record.exc_info)
            }

        try:
            return json.dumps(log_object, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                'timestamp': log_object['timestamp'],
                'level': log_object['level'],
                'message': str(e),
                'error': 'Не удалось сериализовать логи'
            }, ensure_ascii=False)

class Logger:
    """
    Класс для настройки и управления логированием
    """
    def __init__(self):
        self.logs_dir = Path(settings.LOGS_DIR)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger('app')
        self.logger.setLevel(settings.LOG_LEVEL)
        self.logger.handlers.clear()
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """
        Настройка обработчиков логов
        """
        handlers = []

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(CustomJsonFormatter())
        handlers.append(console_handler)

        # Файловый обработчик для всех логов
        file_handler = RotatingFileHandler(
            filename=self.logs_dir / 'portal.log',
            maxBytes=settings.LOG_FILE_MAX_BYTES,
            backupCount=settings.LOG_FILE_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setFormatter(CustomJsonFormatter())
        handlers.append(file_handler)

        # Отдельный файл для ошибок
        error_handler = RotatingFileHandler(
            filename=self.logs_dir / 'error.log',
            maxBytes=settings.LOG_FILE_MAX_BYTES,
            backupCount=settings.LOG_FILE_BACKUP_COUNT,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(CustomJsonFormatter())
        handlers.append(error_handler)

        # Ежедневная ротация для аудита
        audit_handler = TimedRotatingFileHandler(
            filename=self.logs_dir / 'audit.log',
            when='midnight',
            interval=1,
            backupCount=settings.LOG_AUDIT_BACKUP_DAYS,
            encoding='utf-8'
        )
        audit_handler.setFormatter(CustomJsonFormatter())
        handlers.append(audit_handler)

        # Добавляем все обработчики к логгеру
        for handler in handlers:
            self.logger.addHandler(handler)

    def get_logger(self) -> logging.Logger:
        """
        Возвращает настроенный логгер
        """
        return self.logger

    @staticmethod
    def setup_uvicorn_logging() -> Dict[str, Any]:
        """
        Настройка логирования для Uvicorn\n
        Возвращает конфигурацию логирования для Uvicorn
        """
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": CustomJsonFormatter
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "json"
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "json",
                    "filename": str(Path(settings.LOGS_DIR) / "uvicorn.log"),
                    "maxBytes": settings.LOG_FILE_MAX_BYTES,
                    "backupCount": settings.LOG_FILE_BACKUP_COUNT
                }
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["console", "file"],
                    "level": "INFO"
                },
                "uvicorn.error": {
                    "level": "INFO"
                },
                "uvicorn.access": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False
                }
            }
        }

logger = Logger().get_logger()
