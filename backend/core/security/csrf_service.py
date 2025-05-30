# backend/core/security/csrf.py - Защита от CSRF атак

from fastapi import Request, HTTPException, status, Response
from typing import Optional, Set
import secrets
import hmac
import hashlib
import time
from urllib.parse import urlparse

from core.config.config import settings
from core.extensions.logger import logger

class CSRFProtection:
    """
    CSRF защита с токенами и проверкой Origin и CSRF токена в запросе (Single Responsibility и YAGNI принципы)

    Методы:
        - `generate_csrf_token` - Генерирует CSRF токен
        - `verify_token` - Проверяет CSRF токен
        - `verify_origin` - Проверяет Origin
        - `get_token_from_request` - Извлекает CSRF токен из заголовка или cookie запроса
        - `set_csrf_token_cookie` - Устанавливает CSRF токен в cookie

    Зависимости:
        - `csrf_protect` - Декоратор для защиты от CSRF атак
        - `get_csrf_token` - Генерирует новый CSRF токен
    """

    def __init__(self):
        self.secret = settings.CSRF_SECRET.encode()
        self.header_name = settings.CSRF_HEADER_NAME
        self.cookie_name = settings.CSRF_COOKIE_NAME
        self.max_age_seconds = settings.CSRF_TOKEN_EXPIRE_MINUTES * 60
        self.allowed_origins = getattr(settings, 'CORS_ORIGINS', [])
        self.allowed_hosts = self._extract_hosts_from_origins()
        self.check_origin = getattr(settings, 'CSRF_CHECK_ORIGIN', True)
        self.secure = getattr(settings, 'SESSION_COOKIE_SECURE', True)
        self.token_bytes_length = getattr(settings, 'CSRF_TOKEN_BYTES_LENGTH', 32)

    def _extract_hosts_from_origins(self) -> Set[str]:
        """
        Извлекает список хостов из списка origins
        """
        hosts = set()
        for origin in self.allowed_origins:
            try:
                hosts.add(urlparse(origin).netloc)
            except Exception:
                continue
        return hosts

    def _generate_signature(self, message: bytes) -> str:
        """
        Генерирует HMAC подпись\n
        `message` - Сообщение для подписи\n
        Возвращает подпись для сообщения в виде hex строки
        """
        return hmac.new(self.secret, message, hashlib.sha256).hexdigest()


    async def generate_csrf_token(self) -> str:
        """
        Генерация CSRF токена с временной меткой\n
        Возвращает CSRF токен в формате random_hex.timestamp.signature
        """
        try:
            timestamp: str = str(int(time.time()))
            random_hex: str = secrets.token_hex(self.token_bytes_length)
            
            message: bytes = f"{random_hex}.{timestamp}".encode()
            signature: str = self._generate_signature(message)
            
            return f"{random_hex}.{timestamp}.{signature}"
        
        except Exception as err:
            logger.error(f"Ошибка при генерации CSRF токена: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при генерации CSRF токена")

    async def verify_token(self, token: str) -> bool:
        """
        Проверка CSRF токена\n
        `token` - CSRF токен\n
        Возвращает True если токен валиден, False если нет
        """
        if not token:
            logger.warning("[verify_token] Пустой CSRF токен при верификации")
            return False

        try:
            parts = token.split('.')
            if len(parts) != 3:
                logger.warning(f"[verify_token] Неверный формат CSRF токена: {token}")
                return False
                
            random_hex, timestamp_str, signature = parts
            timestamp: int = int(timestamp_str)
            
            # Проверяем срок действия токена
            if (int(time.time()) - timestamp) > self.max_age_seconds:
                logger.warning(f"[verify_token] CSRF токен устарел {(int(time.time()) - timestamp) // 60} минут назад: {token}")
                return False
                
            # Проверяем подпись
            message = f"{random_hex}.{timestamp}".encode()
            expected_signature: str = self._generate_signature(message)
            return hmac.compare_digest(signature, expected_signature)
        
        except (ValueError, IndexError, TypeError):
            return False
        
    async def verify_origin(self, request: Request) -> bool:
        """
        Проверяет, что запрос пришел с разрешенного источника путем проверки заголовков Origin и Referer\n
        Возвращает True, если источник разрешен, иначе False
        """
        if not self.check_origin:
            return True
            
        origin = request.headers.get('Origin')
        referer = request.headers.get('Referer')
        
        # Проверяем Origin заголовок (приоритетный)
        if origin:
            if origin in self.allowed_origins:
                return True
            try:
                host = urlparse(origin).netloc
                return host in self.allowed_hosts
            except Exception:
                pass
                
        # Проверяем Referer
        if referer:
            try:
                host = urlparse(referer).netloc
                return host in self.allowed_hosts
            except Exception:
                pass
                
        # Если ни Origin, ни Referer не прошли проверку
        logger.warning(f"[verify_origin] Запрос с неразрешенного источника: Origin={origin}, Referer={referer}")
        return False
        
    async def get_token_from_request(self, request: Request) -> Optional[str]:
        """
        Извлекает CSRF токен из заголовка или cookie запроса\n
        Возвращает CSRF токен, если он найден, иначе None
        """
        return (
            request.headers.get(self.header_name) or 
            request.cookies.get(self.cookie_name)
        )
    
    async def set_csrf_token_cookie(self, response: Response, csrf_token: str) -> None:
        """
        Установка CSRF токена в cookie\n
        `csrf_token` - CSRF токен для установки в cookie
        """
        response.set_cookie(
            key=self.cookie_name,
            value=csrf_token,
            secure=self.secure,
            samesite="lax",
            httponly=False,
            max_age=self.max_age_seconds,
            path="/"
        )
            
csrf_protection = CSRFProtection()

async def csrf_protect(request: Request) -> None:
    """
    Декоратор для защиты от CSRF атак\n
    Защищает от CSRF атак все запросы кроме GET, HEAD, OPTIONS\n
    Проверяет Origin и CSRF токен
    """
    if request.method in {'GET', 'HEAD', 'OPTIONS'}:
        return
    
    # Проверяем Origin
    if not csrf_protection.verify_origin(request):
        logger.warning(f"[CSRF] Неверный origin для {request.url.path}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Неверный источник запроса")
    
    # Проверяем CSRF токен
    token = csrf_protection.get_token_from_request(request)
    if not token or not csrf_protection.verify_token(token):
        logger.warning(f"[CSRF] Неверный токен для {request.url.path}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Неверный CSRF токен")

def get_csrf_token() -> str:
    """
    Генерирует новый CSRF токен\n
    Возвращает новый CSRF токен
    """
    return csrf_protection.generate_csrf_token()
