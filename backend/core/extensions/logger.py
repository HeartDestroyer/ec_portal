# backend/core/logger.py

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import json
from datetime import datetime
from typing import Any, Dict
from core.config.config import settings

# Кастомный форматтер для логов в JSON формате
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
        Форматирует запись лога в JSON
        
        :param record: Запись лога
        :return: str: Отформатированная запись в JSON
        """
        log_object: Dict[str, Any] = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
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
                log_object[key] = value

        # Добавляем информацию об исключении, если оно есть
        if record.exc_info:
            log_object['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }

        return json.dumps(log_object, ensure_ascii=False)

class Logger:
    """
    Класс для настройки и управления логированием
    """
    def __init__(self):
        # Создаем директорию для логов если её нет
        self.logs_dir = Path(settings.LOGS_DIR)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Инициализируем логгер
        self.logger = logging.getLogger('app')
        self.logger.setLevel(settings.LOG_LEVEL)

        # Очищаем существующие обработчики
        self.logger.handlers.clear()

        # Добавляем обработчики
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """
        Настройка обработчиков логов
        """
        handlers = []

        # Консольный обработчик
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
        
        :return: logging.Logger: Настроенный логгер
        """
        return self.logger

    @staticmethod
    def setup_uvicorn_logging() -> Dict[str, Any]:
        """
        Настройка логирования для Uvicorn
        
        :return: Dict[str, Any]: Конфигурация логирования для Uvicorn
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

# Создаем глобальный экземпляр логгера
logger = Logger().get_logger()
