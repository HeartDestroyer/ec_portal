from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ValidationInfo
from typing import List
from pathlib import Path
import os

class BaseSettingsClass(BaseSettings):
    """
    Базовые настройки приложения
    """
    # Основные настройки
    PROJECT_NAME: str = Field("ЭЦ Портал", env="PROJECT_NAME", description="Название проекта")
    PROJECT_VERSION: str = Field("1.2.0", env="PROJECT_VERSION", description="Версия проекта")
    API_PREFIX: str = Field("", env="API_PREFIX", description="Префикс API")
    SECRET_KEY: str = Field(..., env="SECRET_KEY", description="Секретный ключ приложения")
    DEBUG: bool = Field(False, env="DEBUG", description="Режим отладки")
    ENVIRONMENT: str = Field(..., env="ENVIRONMENT", description="Окружение")
    ADMIN_ROLES: List[str] = Field(["superadmin", "admin"], env="ADMIN_ROLES", description="Роли администраторов")
    EMPLOYEE_ROLES: List[str] = Field(["superadmin", "admin", "leader", "employee"], env="EMPLOYEE_ROLES", description="Роли сотрудников")
    AUTHENTICATED_ROLES: List[str] = Field(["superadmin", "admin", "leader", "employee", "guest"], env="AUTHENTICATED_ROLES", description="Роли аутентифицированных пользователей")
    MAX_ACTIVE_SESSIONS_PER_USER: int = Field(5, env="MAX_ACTIVE_SESSIONS_PER_USER", description="Максимальное количество активных сессий для пользователя")
    DEVELOPER_TG: str = Field("https://t.me/XopXeyLalalei", env="DEVELOPER_TG", description="Телеграм разработчика")
    
    # Настройки push-уведомлений
    VAPID_PRIVATE_KEY: str = Field(..., env="VAPID_PRIVATE_KEY", description="Секретный ключ для push-уведомлений")
    VAPID_PUBLIC_KEY: str = Field(..., env="VAPID_PUBLIC_KEY", description="Публичный ключ для push-уведомлений")
    VAPID_EMAIL: str = Field(..., env="VAPID_EMAIL", description="Почта для push-уведомлений")

    # Сервер
    SERVER_HOST: str = Field("127.0.0.1", env="SERVER_HOST", description="Адрес сервера")
    SERVER_PORT: int = Field(8000, env="SERVER_PORT", description="Порт сервера")
    WORKERS_COUNT: int = Field(4, env="WORKERS_COUNT", description="Количество рабочих процессов")
    LIMIT_CONCURRENCY: int = Field(100, env="LIMIT_CONCURRENCY", description="Количество одновременных запросов")
    TIMEOUT_KEEP_ALIVE: int = Field(5, env="TIMEOUT_KEEP_ALIVE", description="Время ожидания подключения в секундах")

    # Настройки JWT аутентификации
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY", description="Секретный ключ для JWT")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM", description="Алгоритм для JWT")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES", description="Время жизни access токена в минутах")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(14, env="REFRESH_TOKEN_EXPIRE_DAYS", description="Время жизни refresh токена в днях")
    REFRESH_TOKEN_COOKIE: str = Field("refresh_token_cookie", env="REFRESH_TOKEN_COOKIE", description="Имя cookie для refresh токена")
    ACCESS_TOKEN_COOKIE: str = Field("access_token_cookie", env="ACCESS_TOKEN_COOKIE", description="Имя cookie для access токена")

    # Настройки CORS
    CORS_ALLOW_CREDENTIALS: bool = Field(True, env="CORS_ALLOW_CREDENTIALS", description="Разрешение использования credentials в CORS")
    CORS_ALLOW_METHODS: List[str] = Field(["*"], env="CORS_ALLOW_METHODS", description="Методы, разрешенные в CORS")
    CORS_ALLOW_HEADERS: List[str] = Field(["*"], env="CORS_ALLOW_HEADERS", description="Заголовки, разрешенные в CORS")
    CSRF_CHECK_ORIGIN: bool = Field(True, env="CSRF_CHECK_ORIGIN", description="Проверка Origin для CSRF")
    CSRF_TOKEN_BYTES_LENGTH: int = Field(32, env="CSRF_TOKEN_BYTES_LENGTH", description="Длина CSRF токена")

    # Настройки базы данных
    DATABASE_URL: str = Field(..., env="DATABASE_URL", description="URL базы данных")
    SQLALCHEMY_ECHO: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_size": 30,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }

    # Настройки Redis
    REDIS_SSL: bool = Field(False, env="REDIS_SSL", description="Использование SSL для Redis")
    REDIS_URL: str = Field(..., env="REDIS_URL", description="URL Redis")
    REDIS_MAX_CONNECTIONS: int = Field(50, env="REDIS_MAX_CONNECTIONS", description="Максимальное количество подключений к Redis")
    REDIS_TIMEOUT: int = Field(30, env="REDIS_TIMEOUT", description="Время ожидания ответа от Redis в секундах")

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
    SESSION_LIFETIME: int = Field(86400, env="SESSION_LIFETIME", description="Время жизни сессии в секундах")
    CSRF_SECRET: str = Field(..., env="CSRF_SECRET", description="Секретный ключ для CSRF")
    CSRF_TOKEN_EXPIRE_MINUTES: int = Field(30, env="CSRF_TOKEN_EXPIRE_MINUTES", description="Время жизни CSRF токена в минутах")
    CSRF_HEADER_NAME: str = Field("X-CSRF-Token", env="CSRF_HEADER_NAME", description="Имя заголовка CSRF")
    CSRF_COOKIE_NAME: str = Field("csrf_token", env="CSRF_COOKIE_NAME", description="Имя cookie CSRF")
    BCRYPT_ROUNDS: int = Field(12, env="BCRYPT_ROUNDS", description="Количество раундов для bcrypt")
    MIN_LENGTH: int = Field(8, env="MIN_LENGTH", description="Минимальная длина пароля")
    MAX_FAILED_ATTEMPTS: int = Field(5, env="MAX_FAILED_ATTEMPTS", description="Максимальное количество неудачных попыток входа")
    LOCKOUT_DURATION: int = Field(15, env="LOCKOUT_DURATION", description="Время блокировки в секундах")
    SESSION_COOKIE_SECURE: bool = Field(True, env="SESSION_COOKIE_SECURE", description="Использование cookie с флагом secure")

    # Настройки ограничителя запросов
    LIMITER_STORAGE_URI: str = Field(..., env="LIMITER_STORAGE_URI")
    RATELIMIT_DEFAULT: str = Field("200 per day;50 per hour", env="RATELIMIT_DEFAULT", description="Стандартный лимит запросов")
    TIME_RATE_LIMITER: int = Field(60, env="TIME_RATE_LIMITER", description="Время ограничения в секундах")
    SIZE_RATE_LIMITER: int = Field(300, env="SIZE_RATE_LIMITER", description="Максимальное количество запросов в секунду")

    # Настройки кэширования
    CACHE_TYPE: str = Field('RedisCache', env="CACHE_TYPE", description="Тип кэширования")
    CACHE_REDIS_URL: str = Field(..., env="CACHE_REDIS_URL")
    CACHE_DEFAULT_TIMEOUT: int = Field(1800, env="CACHE_DEFAULT_TIMEOUT", description="Время кэширования в секундах")

    # Логирование
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL", description="Уровень логирования")
    LOGS_DIR: Path = Path("logs")
    LOG_FILE_MAX_BYTES: int = Field(10_485_760, env="LOG_FILE_MAX_BYTES", description="Максимальный размер файла лога в байтах")
    LOG_FILE_BACKUP_COUNT: int = Field(5, env="LOG_FILE_BACKUP_COUNT", description="Количество резервных файлов лога")
    LOG_AUDIT_BACKUP_DAYS: int = Field(30, env="LOG_AUDIT_BACKUP_DAYS", description="Количество дней для резервных файлов аудита")

    # Мониторинг
    ENABLE_METRICS: bool = Field(True, env="ENABLE_METRICS", description="Включение мониторинга")
    METRICS_PORT: int = Field(9000, env="METRICS_PORT", description="Порт мониторинга")

    # Настройки Битрикс
    BITRIX_WEBHOOK_URL: str = Field(..., env="BITRIX_WEBHOOK_URL", description="URL вебхука Битрикс")

    # Настройки WebSocket
    WEBSOCKET_PING_INTERVAL: int = Field(20, env="WEBSOCKET_PING_INTERVAL", description="Интервал отправки ping в секундах")
    WEBSOCKET_PING_TIMEOUT: int = Field(20, env="WEBSOCKET_PING_TIMEOUT", description="Таймаут ожидания pong в секундах")
    WEBSOCKET_CLOSE_TIMEOUT: int = Field(20, env="WEBSOCKET_CLOSE_TIMEOUT", description="Таймаут закрытия соединения в секундах")
    WEBSOCKET_MAX_MESSAGE_SIZE: int = Field(1024 * 1024, env="WEBSOCKET_MAX_MESSAGE_SIZE", description="Максимальный размер сообщения в байтах")
    WEBSOCKET_MAX_QUEUE_SIZE: int = Field(64, env="WEBSOCKET_MAX_QUEUE_SIZE", description="Максимальный размер очереди сообщений")
    WEBSOCKET_MAX_CONNECTIONS_PER_USER: int = Field(10, env="WEBSOCKET_MAX_CONNECTIONS_PER_USER", description="Максимальное количество подключений на пользователя")
    WEBSOCKET_CONNECTION_TIMEOUT: int = Field(300, env="CONNECTION_TIMEOUT", description="Время ожидания соединения в секундах")

    class Config:
        env_file = ".env" 
        env_file_encoding = "utf-8"
        extra = 'ignore'

class DevelopmentSettings(BaseSettingsClass):
    """
    Конфигурация для разработки
    """
    DEBUG: bool = True
    SQLALCHEMY_ECHO: bool = True
    CORS_ORIGINS: List[str] = ["http://127.0.0.1:5173"]
    FRONTEND_URL: str = "http://127.0.0.1:5173"

    @field_validator(
        "SECRET_KEY", "VAPID_PRIVATE_KEY", "VAPID_PUBLIC_KEY", "JWT_SECRET_KEY", "JWT_ALGORITHM", "DATABASE_URL", "REDIS_URL",
        "SECURITY_PASSWORD_SALT", "SECRET_KEY_SIGNED_URL", "CSRF_SECRET","LIMITER_STORAGE_URI", "CACHE_REDIS_URL", "BITRIX_WEBHOOK_URL", 
        mode='before'
    )
    @classmethod
    def check_required_vars(cls, error, info: ValidationInfo):
        """
        Проверка обязательных переменных окружения
        """
        if error is None or error == "":
            raise ValueError(f"Обязательная переменная окружения отсутствует: {info.field_name}")
        return error

class ProductionSettings(BaseSettingsClass):
    """
    Конфигурация для продакшена
    """
    DEBUG: bool = False
    REMEMBER_COOKIE_SECURE: bool = True
    CORS_ORIGINS: List[str] = [
        "https://hr.exp-cr.ru", "https://preza.exp-cr.ru", "https://ecgamingstudio.com",
    ]
    FRONTEND_URL: str = "https://hr.exp-cr.ru"
    
    @field_validator(
        "SECRET_KEY", "VAPID_PRIVATE_KEY", "VAPID_PUBLIC_KEY", "JWT_SECRET_KEY", "JWT_ALGORITHM", "DATABASE_URL", "REDIS_URL",
        "SECURITY_PASSWORD_SALT", "SECRET_KEY_SIGNED_URL", "CSRF_SECRET","LIMITER_STORAGE_URI", "CACHE_REDIS_URL", "BITRIX_WEBHOOK_URL", 
        mode='before'
    )
    @classmethod
    def check_required_vars(cls, error, info: ValidationInfo):
        """
        Проверка обязательных переменных окружения\n
        `error` - Ошибка\n
        `info` - Информация о поле\n
        Возвращает ошибку, если переменная окружения отсутствует
        """
        if error is None or error == "":
            raise ValueError(f"Обязательная переменная окружения отсутствует: {info.field_name}")
        return error

def get_settings() -> BaseSettingsClass:
    """
    Получение конфигурации в зависимости от окружения\n
    Возвращает BaseSettingsClass
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    settings_map = {
        "development": DevelopmentSettings,
        "production": ProductionSettings,
    }

    return settings_map.get(env, DevelopmentSettings)()

settings = get_settings()
