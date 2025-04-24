# backend/core/security/csrf.py

from fastapi import Request, HTTPException, status
from typing import Optional, Callable
import secrets
import hmac
import hashlib
import time
from functools import wraps
from core.config.config import BaseSettingsClass, settings

# Класс для защиты от CSRF атак
class CSRFProtection:
    """
    Класс для защиты от CSRF атак
    """
    def __init__(self, settings: BaseSettingsClass):
        self.settings = settings
        self.secret = settings.CSRF_SECRET.encode()
        self.header_name = settings.CSRF_HEADER_NAME
        self.max_age_seconds = settings.CSRF_TOKEN_EXPIRE_MINUTES * 60

    # Генерация CSRF токена с временной меткой
    def generate_token(self) -> str:
        """
        Генерация CSRF токена с временной меткой
        :return: CSRF токен
        """
        timestamp = str(int(time.time()))
        random_bytes = secrets.token_bytes(16)
        message = random_bytes + timestamp.encode()
        signature = hmac.new(self.secret, message, hashlib.sha256).hexdigest()
        token = f"{random_bytes.hex()}.{timestamp}.{signature}"
        return token

    # Проверка CSRF токена
    def verify_token(self, token: str) -> bool:
        """
        Проверка CSRF токена
        :param token: CSRF токен
        :return: True если токен валиден иначе False
        """
        if not token:
            return False
        try:
            random_part, timestamp_str, signature = token.split('.')
            timestamp = int(timestamp_str)
            random_bytes = bytes.fromhex(random_part)
            message = random_bytes + timestamp_str.encode()
            expected_signature = hmac.new(self.secret, message, hashlib.sha256).hexdigest()

            # Проверка подписи
            if not hmac.compare_digest(signature, expected_signature):
                return False

            # Проверка времени жизни токена
            token_age = int(time.time()) - timestamp
            if token_age > self.max_age_seconds:
                return False

            return True
        except (ValueError, AttributeError, TypeError, IndexError):
            return False
        
    # Декоратор для CSRF защиты с гибкими настройками
    def csrf_protect(
        self,
        excluded_paths: Optional[list[str]] = None,
        excluded_methods: Optional[list[str]] = None,
        error_handler: Optional[Callable] = None
    ):
        """
        Декоратор для CSRF защиты с гибкими настройками
        """
        excluded_paths = excluded_paths or []
        excluded_methods = excluded_methods or ['GET', 'HEAD', 'OPTIONS']

        def decorator(func):
            @wraps(func)
            async def wrapper(request: Request, *args, **kwargs):
                # Проверяем исключения
                if request.method in excluded_methods:
                    return await func(request, *args, **kwargs)

                for path in excluded_paths:
                    if request.url.path.startswith(path):
                        return await func(request, *args, **kwargs)

                # Получаем и проверяем токен
                token = request.headers.get('X-CSRF-Token')
                if not token:
                    if error_handler:
                        return await error_handler(request)
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="CSRF token missing"
                    )

                if not self.verify_token(token):
                    if error_handler:
                        return await error_handler(request)
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid CSRF token"
                    )

                return await func(request, *args, **kwargs)
            return wrapper
        return decorator

csrf_handler = CSRFProtection(settings)

# Зависимость для проверки CSRF токена в заголовке
async def csrf_verify_header(
    request: Request,
):
    """
    Проверяет CSRF токен в заголовке для методов, изменяющих состояние
    :param request: Request объект
    """
    csrf_protect_methods = {"POST", "PUT", "DELETE", "PATCH"}
    if request.method not in csrf_protect_methods:
        return # Пропускаем для безопасных методов

    token_from_header = request.headers.get(csrf_handler.header_name)

    # Упрощенная проверка: просто требуем наличие заголовка
    if not csrf_handler.verify_token(token_from_header):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Отсутствует или неверный токен CSRF в заголовке"
        )

