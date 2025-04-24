# core/config/config.py

from pydantic_settings import BaseSettings
from typing import List, Union, Optional
from pathlib import Path
from pydantic import Field, field_validator
import os

# Базовые настройки приложения
class BaseSettingsClass(BaseSettings):
    """
    Базовые настройки приложения
    """
    # Основные настройки
    PROJECT_NAME: str = "ЭЦ Портал"
    PROJECT_VERSION: str = "1.2.0"
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str = Field(..., env="SECRET_KEY", description="Секретный ключ приложения")
    DEBUG: bool = False

    # Сервер
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    WORKERS_COUNT: int = 4
    LIMIT_CONCURRENCY: int = 100
    TIMEOUT_KEEP_ALIVE: int = 5

    # Настройки JWT аутентификации
    JWT_SECRET_KEY: str = Field(..., env="SECRET_KEY", description="Секретный ключ для JWT")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Настройки CORS
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # Настройки базы данных
    DATABASE_URL: str = Field(..., env="DATABASE_URL", description="URL базы данных")
    SQLALCHEMY_ECHO: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_size": 30,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }

    # Настройки Redis
    REDIS_HOST: str = Field(..., env="REDIS_HOST", description="Хост Redis")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT", description="Порт Redis")
    REDIS_DB: int = 0 
    REDIS_PASSWORD: Optional[str] = Field(None, env="REDIS_PASSWORD", description="Пароль Redis")
    REDIS_SSL: bool = True
    REDIS_URL: Optional[str] = Field(None, env="REDIS_URL", description="URL Redis")

    # Настройки почты
    MAIL_USERNAME: Optional[str] = Field(None, env="MAIL_USERNAME")
    MAIL_PASSWORD: Optional[str] = Field(None, env="MAIL_PASSWORD")
    MAIL_PORT: int = Field(465, env="MAIL_PORT")
    MAIL_SERVER: str = Field("smtp.gmail.com", env="MAIL_SERVER")
    MAIL_DEFAULT_SENDER: Optional[str] = Field(None, env="MAIL_DEFAULT_SENDER")
    MAIL_TLS: bool = False
    MAIL_SSL: bool = True

    # Настройки безопасности
    SECURITY_PASSWORD_SALT: str = Field(..., env="SECURITY_PASSWORD_SALT")
    SESSION_LIFETIME: int = 86400
    CSRF_SECRET: str = Field(..., env="CSRF_SECRET", description="Секретный ключ для CSRF")
    CSRF_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Настройки ограничителя запросов
    LIMITER_STORAGE_URI: str = Field(..., env="REDIS_URL")
    RATELIMIT_DEFAULT: str = "200 per day;50 per hour"
    TIME_RATE_LIMITER: int = 60
    SIZE_RATE_LIMITER: int = 300

    # Настройки кэширования
    CACHE_TYPE: str = 'RedisCache'
    CACHE_REDIS_URL: str = Field(..., env="REDIS_URL")
    CACHE_DEFAULT_TIMEOUT: int = 1800

    # Логирование
    LOG_LEVEL: str = "INFO"
    LOGS_DIR: Path = Path("logs")
    LOG_FILE_MAX_BYTES: int = 10_485_760
    LOG_FILE_BACKUP_COUNT: int = 5
    LOG_AUDIT_BACKUP_DAYS: int = 30

    # Мониторинг
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9000

# Конфигурация для разработки
class DevelopmentSettings(BaseSettingsClass):
    """
    Конфигурация для разработки
    """
    DEBUG = True
    SQLALCHEMY_ECHO = True
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

# Конфигурация для продакшена
class ProductionSettings(BaseSettingsClass):
    """
    Конфигурация для продакшена
    """
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    CORS_ORIGINS: List[str] = [
        "https://hr.exp-cr.ru",
        "https://preza.exp-cr.ru",
        "https://ecgamingstudio.com",
    ]
    
    # Проверка обязательных переменных окружения
    @field_validator("SECRET_KEY", "DATABASE_URL", "REDIS_HOST", "CSRF_SECRET", pre=True)
    def check_required_vars(cls, error, field: Field):
        """
        Проверка обязательных переменных окружения
        """
        if not error:
            raise ValueError(f"Обязательная переменная окружения отсутствует: {field.name}")
        return error

# Выбор конфигурации в зависимости от окружения
def get_settings() -> BaseSettingsClass:
    """
    Получение конфигурации в зависимости от окружения
    """
    env = os.getenv("FASTAPI_ENV", "development").lower()
    settings_map = {
        "development": DevelopmentSettings,
        "production": ProductionSettings,
    }
    return settings_map.get(env, DevelopmentSettings)()

settings = get_settings()
