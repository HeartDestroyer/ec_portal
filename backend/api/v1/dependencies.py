"""
Файл зависимостей для API v1
Включает в себя:
- Обработку исключений
- Получение access и refresh токенов из запроса
- Проверку роли пользователя
- Декораторы для доступа к API:
    - require_admin_roles - для доступа администратору
    - require_not_guest - для доступа сотруднику
    - require_authenticated - для доступа авторизованному пользователю
"""

from fastapi import Request, HTTPException, status
from functools import wraps
from typing import List, Optional, Callable, Any, Dict, TypeVar
import traceback
import inspect

from core.extensions.logger import logger
from core.extensions.database import get_db
from core.extensions.redis import get_redis
from core.config.config import BaseSettingsClass, get_settings, settings
from core.security.jwt import (
    get_current_user_payload, get_current_active_user, jwt_handler, JWTHandler
)
from core.security.csrf import csrf_verify_header, CSRFProtection
from core.security.email import email_manager, EmailManager
from core.security.session import SessionManager
from .schemas import TokenPayload

T = TypeVar('T')
DecoratedFunc = TypeVar('DecoratedFunc', bound=Callable[..., Any])

AUTH_HEADER_NAME = "Authorization"
BEARER_PREFIX = "Bearer "

def handle_exception(
    error: Exception, 
    error_message: str = "Произошла ошибка",
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    include_trace: bool = True
) -> None:
    """
    Обрабатывает исключения, логирует сообщения об ошибках и поднимает HTTPException\n
    `error` - Исключение для обработки\n
    `error_message` - Сообщение об ошибке для логирования и возврата пользователю\n
    `status_code` - HTTP статус-код, возвращаемый пользователю (по умолчанию 500)\n
    `include_trace` - Флаг для включения стека вызовов в лог (по умолчанию True)
    """
    if isinstance(error, HTTPException):
        raise error
    
    # Получаем стек вызовов для более подробного логирования
    stack_trace = traceback.format_exc() if include_trace else "Стек вызовов отключен"
    
    # Определяем исходный файл и строку ошибки
    error_frame = inspect.trace()[-1]
    error_file = error_frame.filename.split('/')[-1]
    error_line = error_frame.lineno
    error_location = f"{error_file}:{error_line}"
    
    # Формируем детальное сообщение с типом ошибки, местоположением и оригинальным сообщением
    error_type = type(error).__name__
    detailed_msg = f"{error_message} [{error_type} в {error_location}]: {str(error)}"
    
    # Логируем с разным уровнем в зависимости от статус-кода
    if status_code >= 500:
        logger.error(f"{detailed_msg}\nСтек вызовов:\n{stack_trace}")
    elif status_code >= 400:
        logger.warning(f"{detailed_msg}")
        if include_trace:
            logger.debug(f"Стек вызовов для предупреждения:\n{stack_trace}")
    else:
        logger.info(f"{detailed_msg}")
    
    # В продакшене возвращаем пользователю упрощенное сообщение
    is_production = settings.ENVIRONMENT == "production"
    exception_detail = error_message if is_production else f"{error_message} [{error_type}: {str(error)}]"
    
    raise HTTPException(status_code=status_code, detail=exception_detail)

async def get_access_token_from_request(request: Request) -> str:
    """
    Получает access токен доступа из запроса, проверяя cookie и заголовок Authorization\n
    Возвращает токен доступа в виде строки
    """
    try:
        token = request.cookies.get(jwt_handler.access_cookie_name)
        logger.debug(f"[get_token_from_request] access_token: {token}")
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Отсутствует токен доступа")
        return token
        
    except HTTPException:
        raise
    except Exception as err:
        handle_exception(err, "Ошибка при получении токена доступа", status.HTTP_401_UNAUTHORIZED)

async def get_refresh_token_from_request(request: Request) -> str:
    """
    Получает refresh токен доступа из запроса\n
    Возвращает токен доступа в виде строки
    """
    try:
        token = request.cookies.get(jwt_handler.refresh_cookie_name)
        logger.debug(f"[get_token_from_request] refresh_token: {token}")
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Токен обновления отсутствует")
        return token
        
    except HTTPException:
        raise
    except Exception as err:
        handle_exception(err, "Ошибка при получении токена обновления", status.HTTP_401_UNAUTHORIZED)

def extract_request(args, kwargs) -> Optional[Request]:
    """
    Унифицированное получение объекта запроса Request\n
    `args` - Аргументы функции\n
    `kwargs` - Ключевые аргументы функции\n
    Возвращает объект запроса Request, или бросает HTTPException если не найден
    """
    try:
        # Сначала проверяем kwargs, так как это более прямой способ
        if "request" in kwargs and isinstance(kwargs["request"], Request):
            return kwargs["request"]
        
        # Затем ищем в позиционных аргументах
        for arg in args:
            if isinstance(arg, Request):
                return arg
                
        logger.warning("Не удалось получить объект запроса")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не удалось получить объект запроса")
        
    except Exception as err:
        logger.error(f"Непредвиденная ошибка при извлечении объекта запроса: {err}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не удалось получить объект запроса")

async def check_role(request: Request, allowed_roles: List[str]) -> TokenPayload:
    """
    Проверка наличия access токена и роли пользователя\n
    `request` - Объект запроса\n
    `allowed_roles` - Список разрешенных ролей\n
    Возвращает payload токена в виде TokenPayload
    """
    redis = await get_redis()
    access_token = await get_access_token_from_request(request)
    payload = await jwt_handler.verify_token(access_token, "access", redis)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Отсуствует токен доступа")
    
    if payload.role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для выполнения операции")
    return payload


def require_admin_roles(allowed_roles: Optional[List[str]] = None):
    """
    Декоратор для доступа администраторам\n 
    `allowed_roles` - Список разрешенных ролей\n 
    По умолчанию разрешены роли из настроек ADMIN_ROLES
    """
    if allowed_roles is None:
        allowed_roles = settings.ADMIN_ROLES

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Dict[str, Any]):
            request = extract_request(args, kwargs)
            try:
                await check_role(request, allowed_roles)
                return await func(*args, **kwargs)

            except HTTPException as err:
                raise err
            except Exception as err:
                handle_exception(err, "Ошибка при проверке прав доступа", status.HTTP_500_INTERNAL_SERVER_ERROR)
        return wrapper
    return decorator

def require_not_guest(allowed_roles: Optional[List[str]] = None):
    """
    Декоратор для доступа сотрудникам\n 
    `allowed_roles` - Список разрешенных ролей\n 
    По умолчанию разрешены роли из настроек EMPLOYEE_ROLES
    """
    if allowed_roles is None:
        allowed_roles = settings.EMPLOYEE_ROLES

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Dict[str, Any]):
            request = extract_request(args, kwargs)
            try:
                await check_role(request, allowed_roles)
                return await func(*args, **kwargs)
            except HTTPException as err:
                raise err
            except Exception as err:
                handle_exception(err, "Ошибка при проверке прав доступа", status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        return wrapper
    return decorator

def require_authenticated():
    """
    Декоратор для проверки, что пользователь аутентифицирован\n
    По умолчанию разрешены роли из настроек AUTHENTICATED_ROLES
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Dict[str, Any]):
            request = extract_request(args, kwargs)
            try:
                await check_role(request, settings.AUTHENTICATED_ROLES)
                return await func(*args, **kwargs)

            except HTTPException as err:
                raise err
            except Exception as err:
                handle_exception(err, "Ошибка при проверке аутентификации", status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        return wrapper
    return decorator

__all__ = [
    "get_db",
    "get_redis",
    "get_settings",
    "settings",
    "BaseSettingsClass",
    "logger",
    "jwt_handler",
    "JWTHandler",
    "email_manager",
    "EmailManager",
    "CSRFProtection",
    "SessionManager",
    "csrf_verify_header",
    "get_access_token_from_request",
    "get_refresh_token_from_request",
    "get_current_user_payload",
    "get_current_active_user",
    "require_admin_roles",
    "require_not_guest",
    "require_authenticated",
    "handle_exception"
]
