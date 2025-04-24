# backend/api/dependencies.py

from core.extensions.database import get_db
from core.extensions.redis import get_redis
from core.config.config import get_settings, Settings
from core.security.jwt import (
    get_current_user_payload,
    get_current_active_user
)
from core.security.csrf import csrf_verify_header # Если используем CSRF

# Переэкспортируем зависимости для удобства
__all__ = [
    "get_db",
    "get_redis",
    "get_settings",
    "Settings",
    "get_current_user_payload",
    "get_current_active_user",
    "csrf_verify_header", # Если используем CSRF
]
