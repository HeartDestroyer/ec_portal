from fastapi import Request, HTTPException, status, Response
from typing import Optional, Callable, List, Any, Dict, Set, Tuple
import secrets
import hmac
import hashlib
import time
from functools import wraps
from urllib.parse import urlparse

from core.config.config import settings
from core.extensions.logger import logger

class CSRFProtection:
    """
    Класс для защиты от CSRF атак\n
    Методы:
    - `generate_token` - Генерация CSRF токена
    - `verify_token` - Проверка CSRF токена
    - `verify_origin` - Проверка заголовков Origin/Referer
    - `set_csrf_token_cookie` - Установка CSRF токена в cookie
    - `get_token_from_request` - Извлечение CSRF токена из заголовка или cookie запроса
    - `_cleanup_token_cache` - Очистка кэша токенов при необходимости
    - `_generate_signature` - Генерация подписи для сообщения
    - `csrf_protect` - Декоратор для CSRF защиты с гибкими настройками
    - `csrf_verify_header` - Проверка CSRF токена в заголовке для методов, изменяющих состояние
    - `get_csrf_protection_dependency` - Возвращает зависимость FastAPI для включения CSRF защиты в маршруты
    """

    def __init__(self):
        # Основные настройки CSRF защиты
        self.secret = settings.CSRF_SECRET.encode()
        self.header_name = settings.CSRF_HEADER_NAME
        self.max_age_seconds = settings.CSRF_TOKEN_EXPIRE_MINUTES * 60
        self.csrf_cookie_name = settings.CSRF_COOKIE_NAME
        self.secure = settings.SESSION_COOKIE_SECURE if hasattr(settings, 'SESSION_COOKIE_SECURE') else True
        
        # Список доверенных источников
        self.allowed_origins = settings.CORS_ORIGINS if hasattr(settings, 'CORS_ORIGINS') else []
        self.allowed_hosts = self._extract_hosts_from_origins(self.allowed_origins)
        
        # Параметры безопасности
        self.token_bytes_length = 32  # Увеличенная длина для большей энтропии
        self.check_origin = settings.CSRF_CHECK_ORIGIN if hasattr(settings, 'CSRF_CHECK_ORIGIN') else True
        
        # Кэш токенов для ускорения проверки
        self.token_cache: Dict[str, Tuple[int, str]] = {}
        # Лимит размера кэша
        self.token_cache_max_size = 10000
        # Период очистки кэша в секундах
        self.token_cache_cleanup_interval = 300
        self.last_cache_cleanup = time.time()
        
        logger.debug("Инициализирован CSRFProtection с настройками: "
                    f"header_name={self.header_name}, check_origin={self.check_origin}, "
                    f"allowed_hosts={self.allowed_hosts}")

    def _extract_hosts_from_origins(self, origins: List[str]) -> Set[str]:
        """
        Извлекает список хостов из списка origins
        Для повышения производительности проверки заголовков
        """
        hosts = set()
        for origin in origins:
            try:
                parsed = urlparse(origin)
                host = parsed.netloc
                if host:
                    hosts.add(host)
            except Exception as e:
                logger.warning(f"Не удалось распарсить origin {origin}: {e}")
        return hosts

    def _cleanup_token_cache(self, force: bool = False) -> None:
        """
        Очищает кэш токенов от устаревших записей
        """
        current_time = time.time()
        
        # Проверяем, не пришло ли время для очистки кэша
        if not force and (current_time - self.last_cache_cleanup) < self.token_cache_cleanup_interval:
            return
            
        # Очищаем устаревшие токены
        expired_tokens = []
        for token, (timestamp, _) in self.token_cache.items():
            if (current_time - timestamp) > self.max_age_seconds:
                expired_tokens.append(token)
                
        # Удаляем устаревшие токены из кэша
        for token in expired_tokens:
            del self.token_cache[token]
            
        # Если кэш все равно слишком большой, удаляем самые старые токены
        if len(self.token_cache) > self.token_cache_max_size:
            sorted_items = sorted(self.token_cache.items(), key=lambda x: x[1][0])
            tokens_to_remove = sorted_items[:len(self.token_cache) - self.token_cache_max_size]
            for token, _ in tokens_to_remove:
                del self.token_cache[token]
                
        self.last_cache_cleanup = current_time
        logger.debug(f"CSRF token кэш очищен. Удалено {len(expired_tokens)} токенов. Текущий размер кэша: {len(self.token_cache)}")


    def _generate_signature(self, message: bytes) -> str:
        """
        Метод для генерации подписи для сообщения\n
        `message` - Сообщение для подписи\n
        Возвращает подпись для сообщения в виде hex строки
        """
        return hmac.new(self.secret, message, hashlib.sha256).hexdigest()

    def generate_token(self) -> str:
        """
        Генерация `CSRF` токена с временной меткой\n
        Возвращает `CSRF` токен в формате random_hex.timestamp.signature
        """
        try:
            timestamp: str = str(int(time.time()))
            random_bytes: bytes = secrets.token_bytes(self.token_bytes_length)
            random_hex: str = random_bytes.hex()
            
            # Base message is random bytes + timestamp
            message: bytes = random_bytes + timestamp.encode()
            signature: str = self._generate_signature(message)
            
            token: str = f"{random_hex}.{timestamp}.{signature}"
            
            # Кэшируем токен для быстрой проверки
            self.token_cache[token] = (int(timestamp), signature)
            
            # Выполняем очистку кэша при необходимости
            self._cleanup_token_cache()
            
            logger.debug(f"Сгенерирован новый CSRF токен с временной меткой {timestamp}")
            return token
        
        except Exception as err:
            logger.error(f"Ошибка при генерации CSRF токена: {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при генерации CSRF токена"
            )

    def verify_token(self, token: str) -> bool:
        """
        Проверка CSRF токена\n
        `token` - CSRF токен\n
        Возвращает True если токен валиден, False если нет
        """
        if not token:
            logger.warning("Пустой CSRF токен при проверке")
            return False

        try:
            # Проверяем формат токена
            parts = token.split('.')
            if len(parts) != 3:
                logger.warning(f"Неверный формат CSRF токена: {token}")
                return False
                
            random_part, timestamp_str, signature = parts
            
            # Проверяем кэш для ускорения проверки
            cached_data = self.token_cache.get(token)
            if cached_data:
                cached_timestamp, cached_signature = cached_data
                
                # Проверяем истечение срока действия токена
                token_age = int(time.time()) - cached_timestamp
                if token_age <= self.max_age_seconds:
                    return True
                else:
                    # Удаляем устаревший токен из кэша
                    del self.token_cache[token]
                    logger.debug(f"CSRF токен устарел (возраст: {token_age} сек)")
                    return False
            
            # Если токена нет в кэше, проверяем обычным способом
            timestamp: int = int(timestamp_str)
            current_time = int(time.time())
            token_age = current_time - timestamp
            
            # Проверяем возраст токена
            if token_age > self.max_age_seconds:
                logger.warning(f"CSRF токен устарел: возраст {token_age} сек > {self.max_age_seconds} сек")
                return False
                
            # Проверяем подпись
            random_bytes: bytes = bytes.fromhex(random_part)
            message: bytes = random_bytes + timestamp_str.encode()
            expected_signature: str = self._generate_signature(message)
            
            # Безопасное сравнение для предотвращения timing attacks
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("Неверная подпись CSRF токена")
                return False
            
            # Кэшируем валидный токен для ускорения будущих проверок
            self.token_cache[token] = (timestamp, signature)
            return True
        
        except (ValueError, AttributeError, TypeError, IndexError) as err:
            logger.error(f"Ошибка при проверке CSRF токена: {err}")
            return False
        except Exception as err:
            logger.error(f"Непредвиденная ошибка при проверке CSRF токена: {err}", exc_info=True)
            return False
        
    def verify_origin(self, request: Request) -> bool:
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
            # Проверка по полному совпадению с доверенными источниками
            if origin in self.allowed_origins:
                return True
                
            # Проверка по хосту
            try:
                parsed_origin = urlparse(origin)
                origin_host = parsed_origin.netloc
                if origin_host in self.allowed_hosts:
                    return True
            except Exception as e:
                logger.warning(f"Ошибка при разборе заголовка Origin ({origin}): {e}")
                
        # Если Origin отсутствует, проверяем Referer
        elif referer:
            try:
                parsed_referer = urlparse(referer)
                referer_host = parsed_referer.netloc
                
                if referer_host in self.allowed_hosts:
                    return True
            except Exception as err:
                logger.warning(f"Ошибка при разборе заголовка Referer ({referer}): {err}")
                
        # Если ни Origin, ни Referer не прошли проверку
        logger.warning(f"Запрос с неразрешенного источника: Origin={origin}, Referer={referer}")
        return False
        
    async def set_csrf_token_cookie(self, response: Response, csrf_token: str) -> None:
        """
        Установка CSRF токена в cookie\n
        `response` - Объект ответа FastAPI\n
        `csrf_token` - CSRF токен для установки в cookie
        """
        try:
            response.set_cookie(
                key=self.csrf_cookie_name,
                value=csrf_token,
                secure=self.secure,
                samesite="lax",
                httponly=False,
                max_age=self.max_age_seconds,
                path="/"
            )
            
        except Exception as err:
            logger.error(f"Ошибка при установке CSRF токена в cookie: {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при установке CSRF токена в cookie"
            )

    def generate_csrf_token(self) -> str:
        """
        Генерация CSRF токена для AJAX-запросов
        Возвращает CSRF токен с улучшенной энтропией
        """
        try:
            # Используем более длинный и безопасный токен
            random_part = secrets.token_hex(32)  # 64 символа в hex-строке
            timestamp = str(int(time.time()))
            message = f"{random_part}{timestamp}".encode()
            signature = self._generate_signature(message)
            
            token = f"{random_part}.{timestamp}.{signature}"
            
            # Кэшируем токен
            self.token_cache[token] = (int(timestamp), signature)
            
            # Очистка кэша при необходимости
            self._cleanup_token_cache()
            
            return token
        
        except Exception as err:
            logger.error(f"Ошибка при генерации CSRF токена: {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при генерации CSRF токена"
            )
            
    def get_token_from_request(self, request: Request) -> Optional[str]:
        """
        Извлекает CSRF токен из заголовка или cookie запроса
        """
        # Сначала проверяем заголовок
        token = request.headers.get(self.header_name)
        if token:
            return token
            
        # Если в заголовке нет, проверяем cookie
        cookies = request.cookies
        if self.csrf_cookie_name in cookies:
            return cookies[self.csrf_cookie_name]
            
        return None

def csrf_protect(
    excluded_paths: Optional[List[str]] = None, 
    excluded_methods: Optional[List[str]] = None, 
    error_handler: Optional[Callable] = None,
    check_origin: bool = True,
) -> Callable:
    """
    Декоратор для CSRF защиты с гибкими настройками\n
    `excluded_paths` - Список путей, которые не требуют CSRF защиты\n
    `excluded_methods` - Список методов, которые не требуют CSRF защиты\n
    `error_handler` - Обработчик ошибок\n
    `check_origin` - Проверять ли заголовки Origin/Referer\n
    Возвращает декоратор
    """
    excluded_paths: List[str] = excluded_paths or []
    excluded_methods: List[str] = excluded_methods or ['GET', 'HEAD', 'OPTIONS']
    csrf_handler = CSRFProtection()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args: Any, **kwargs: Any) -> Any:
            # Проверка на исключение по методу
            if request.method in excluded_methods:
                return await func(request, *args, **kwargs)

            # Проверка на исключение по пути
            for path in excluded_paths:
                if request.url.path.startswith(path):
                    return await func(request, *args, **kwargs)
                    
            try:
                # Проверка заголовков Origin/Referer при необходимости
                if check_origin and not csrf_handler.verify_origin(request):
                    logger.warning(f"CSRF атака: неправильный Origin/Referer для {request.url.path}")
                    if error_handler:
                        return await error_handler(request)
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Запрос с неразрешенного источника"
                    )

                # Получение и проверка CSRF токена
                token = csrf_handler.get_token_from_request(request)
                if not token:
                    logger.warning(f"CSRF атака: отсутствует токен для {request.url.path}")
                    if error_handler:
                        return await error_handler(request)
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Отсутствует CSRF токен в заголовке {csrf_handler.header_name}"
                    )

                if not csrf_handler.verify_token(token):
                    logger.warning(f"CSRF атака: недействительный токен для {request.url.path}")
                    if error_handler:
                        return await error_handler(request)
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Недействительный CSRF токен"
                    )

                # Если все проверки пройдены, вызываем оригинальную функцию
                return await func(request, *args, **kwargs)
            
            except HTTPException:
                raise
            except Exception as err:
                logger.error(f"Ошибка в CSRF защите: {err}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Ошибка в CSRF защите"
                )
        return wrapper
    return decorator

csrf_handler = CSRFProtection()

async def csrf_verify_header(request: Request) -> None:
    """
    Проверяет CSRF токен в заголовке для методов, изменяющих состояние\n
    Используется как зависимость FastAPI
    """
    try:
        # Проверяем только для методов, изменяющих состояние
        csrf_protect_methods = {"POST", "PUT", "DELETE", "PATCH"}
        if request.method not in csrf_protect_methods:
            return

        # Проверка заголовков Origin/Referer
        if not csrf_handler.verify_origin(request):
            logger.warning(f"CSRF защита: неверный Origin/Referer для {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Запрос с неразрешенного источника"
            )

        # Получение и проверка токена
        token = csrf_handler.get_token_from_request(request)
        if not token:
            logger.warning(f"CSRF защита: отсутствует токен для {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Отсутствует CSRF токен в заголовке {csrf_handler.header_name}"
            )

        if not csrf_handler.verify_token(token):
            logger.warning(f"CSRF защита: недействительный токен для {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недействительный CSRF токен"
            )
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Ошибка при проверке CSRF заголовка: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при проверке CSRF заголовка"
        )
        
def get_csrf_protection_dependency() -> Callable:
    """
    Возвращает зависимость FastAPI для включения CSRF защиты в маршруты\n
    Пример использования:
        @app.post("/api/example", dependencies=[Depends(get_csrf_protection_dependency())])
    """
    return csrf_verify_header
