# backend/api/dependencies.py

from core.extensions.database import get_db
from core.extensions.redis import get_redis
from core.config.config import BaseSettingsClass, get_settings, settings
from core.security.jwt import get_current_user_payload, get_current_active_user, jwt_handler
from core.security.csrf import csrf_verify_header # Если используем CSRF
from fastapi import Request, HTTPException, status
from functools import wraps
from typing import List, Optional, Callable

# Декоратор для проверки роли администратора
def require_admin_roles(allowed_roles: Optional[List[str]] = None):
    """
    Декоратор для проверки роли администратора
    :param `allowed_roles`: Список разрешенных ролей\n 
    По умолчанию ["admin", "superadmin"]
    """
    if allowed_roles is None:
        allowed_roles = ["admin", "superadmin"]

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request')
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Не удалось получить объект запроса"
                )

            refresh_token = request.cookies.get(jwt_handler.refresh_cookie_name)
            
            if not refresh_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh токен отсутствует"
                )

            redis = await get_redis()

            try:
                payload = await jwt_handler.verify_token(refresh_token, "refresh", redis)
                if not payload:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Невалидный refresh токен"
                    )

                user_role = payload.get("role")
                if user_role not in allowed_roles:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Недостаточно прав для выполнения операции"
                    )

                return await func(*args, **kwargs)

            except HTTPException as err:
                raise err
            except Exception as err:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Ошибка при проверке прав доступа: {err}"
                )

        return wrapper
    return decorator

# Переэкспортируем зависимости для удобства
__all__ = [
    "get_db",
    "get_redis",
    "get_settings",
    "settings",
    "BaseSettingsClass",
    "get_current_user_payload",
    "get_current_active_user",
    "csrf_verify_header", # Если используем CSRF
    "require_admin_roles", # Добавляем декоратор в экспорт
]
