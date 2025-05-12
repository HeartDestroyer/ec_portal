# core/config/config.py

from pydantic_settings import BaseSettings
from typing import List, Optional
from pathlib import Path
from pydantic import Field, field_validator, ValidationInfo
import os

# Базовые настройки приложения
class BaseSettingsClass(BaseSettings):
    """
    Базовые настройки приложения
    """
    # Основные настройки
    PROJECT_NAME: str = "ЭЦ Портал"
    PROJECT_VERSION: str = "1.2.0"
    API_PREFIX: str = ""
    SECRET_KEY: str = Field(..., env="SECRET_KEY", description="Секретный ключ приложения")
    DEBUG: bool = False
    ENVIRONMENT: str = Field(..., env="ENVIRONMENT", description="Окружение")

    # Сервер
    SERVER_HOST: str = "127.0.0.1"
    SERVER_PORT: int = 8000
    WORKERS_COUNT: int = 4
    LIMIT_CONCURRENCY: int = 100
    TIMEOUT_KEEP_ALIVE: int = 5

    # Настройки JWT аутентификации
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY", description="Секретный ключ для JWT")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_TOKEN_COOKIE: str = "refresh_token_cookie"
    ACCESS_TOKEN_COOKIE: str = "access_token_cookie"

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
    REDIS_SSL: bool = False
    REDIS_URL: str = Field(..., env="REDIS_URL", description="URL Redis")
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_TIMEOUT: int = 15

    # Настройки почты
    MAIL_USERNAME: str = Field(..., env="MAIL_USERNAME")
    MAIL_PASSWORD: str = Field(..., env="MAIL_PASSWORD")
    MAIL_PORT: int = Field(465, env="MAIL_PORT")
    MAIL_SERVER: str = Field(..., env="MAIL_SERVER")
    MAIL_DEFAULT_SENDER: str = Field(..., env="MAIL_DEFAULT_SENDER")
    MAIL_TLS: bool = Field(False, env="MAIL_TLS")
    MAIL_SSL: bool = Field(True, env="MAIL_SSL")

    # Настройки безопасности
    SECURITY_PASSWORD_SALT: str = Field(..., env="SECURITY_PASSWORD_SALT", description="Секретный ключ для безопасности паролей")
    SECRET_KEY_SIGNED_URL: str = Field(..., env="SECRET_KEY_SIGNED_URL", description="Секретный ключ для подписанных URL")
    SESSION_LIFETIME: int = 86400
    CSRF_SECRET: str = Field(..., env="CSRF_SECRET", description="Секретный ключ для CSRF")
    CSRF_TOKEN_EXPIRE_MINUTES: int = 30
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    CSRF_COOKIE_NAME: str = "csrf_token"
    BCRYPT_ROUNDS: int = 12
    MIN_LENGTH: int = 8
    MAX_FAILED_ATTEMPTS: int = 5
    LOCKOUT_DURATION: int = 15


    # Настройки ограничителя запросов
    LIMITER_STORAGE_URI: str = Field(..., env="LIMITER_STORAGE_URI")
    RATELIMIT_DEFAULT: str = "200 per day;50 per hour"
    TIME_RATE_LIMITER: int = 60
    SIZE_RATE_LIMITER: int = 300

    # Настройки кэширования
    CACHE_TYPE: str = 'RedisCache'
    CACHE_REDIS_URL: str = Field(..., env="CACHE_REDIS_URL")
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

    class Config:
        env_file = ".env" 
        env_file_encoding = "utf-8"
        extra = 'ignore'

# Конфигурация для разработки
class DevelopmentSettings(BaseSettingsClass):
    """
    Конфигурация для разработки
    """
    DEBUG: bool = True
    SQLALCHEMY_ECHO: bool = True
    CORS_ORIGINS: List[str] = ["http://127.0.0.1:5173"]
    FRONTEND_URL: str = "http://127.0.0.1:5173"

    # Проверка обязательных переменных окружения
    @field_validator("SECRET_KEY", "DATABASE_URL", "REDIS_URL", "CSRF_SECRET", "SECURITY_PASSWORD_SALT", "JWT_SECRET_KEY", mode='before')
    @classmethod
    def check_required_vars(cls, error, info: ValidationInfo):
        """
        Проверка обязательных переменных окружения
        """
        if error is None or error == "":
            raise ValueError(f"Обязательная переменная окружения отсутствует: {info.field_name}")
        return error

# Конфигурация для продакшена
class ProductionSettings(BaseSettingsClass):
    """
    Конфигурация для продакшена
    """
    DEBUG: bool = False
    SESSION_COOKIE_SECURE: bool = True
    REMEMBER_COOKIE_SECURE: bool = True
    CORS_ORIGINS: List[str] = [
        "https://hr.exp-cr.ru",
        "https://preza.exp-cr.ru",
        "https://ecgamingstudio.com",
    ]
    FRONTEND_URL: str = "https://hr.exp-cr.ru"
    
    # Проверка обязательных переменных окружения
    @field_validator("SECRET_KEY", "DATABASE_URL", "REDIS_URL", "CSRF_SECRET", "SECURITY_PASSWORD_SALT", "JWT_SECRET_KEY", mode='before')
    @classmethod
    def check_required_vars(cls, error, info: ValidationInfo):
        """
        Проверка обязательных переменных окружения
        """
        if error is None or error == "":
            raise ValueError(f"Обязательная переменная окружения отсутствует: {info.field_name}")
        return error

# Выбор конфигурации в зависимости от окружения
def get_settings() -> BaseSettingsClass:
    """
    Получение конфигурации в зависимости от окружения
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    settings_map = {
        "development": DevelopmentSettings,
        "production": ProductionSettings,
    }

    return settings_map.get(env, DevelopmentSettings)()

settings = get_settings()
