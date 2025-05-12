# backend/core/security/jwt.py

# Импортируем зависимости
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from core.config.config import BaseSettingsClass, settings, ProductionSettings
from core.extensions.redis import get_redis
from core.extensions.database import get_db 
from core.models.user import User
from core.extensions.logger import logger

# Схема OAuth2 для получения токена из заголовка Authorization: Bearer <token>
# tokenUrl - это эндпоинт для получения токена (логина)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Класс для работы с JWT токенами
class JWTHandler:
    """
    Класс для работы с JWT токенами
    
    :`create_refresh_token`: Создание refresh токена для пользователя
    :`create_access_token`: Создание access токена для пользователя
    :`create_tokens`: Создание пары токенов для пользователя
    :`verify_token`: Проверка JWT токена
    :`set_refresh_token_cookie`: Установка refresh токена в cookie
    :`set_access_token_cookie`: Установка access токена в cookie
    :`revoke_tokens`: Отзыв токенов пользователя
    """
    def __init__(self, settings: BaseSettingsClass):
        self.settings = settings
        self.access_token_expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        self.refresh_token_expire = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        self.algorithm = settings.JWT_ALGORITHM
        self.secret_key = settings.JWT_SECRET_KEY
        self.refresh_cookie_name = settings.REFRESH_TOKEN_COOKIE
        self.access_cookie_name = settings.ACCESS_TOKEN_COOKIE

    # Создание access токена
    async def create_access_token(self, data: Dict[str, Any], redis: Redis) -> str:
        """
        Создание `access` токена с сохранением в Redis
        :param `data`: Данные пользователя
        :param `redis`: Redis клиент
        :return: Access токен
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + self.access_token_expire
        to_encode.update({"exp": expire, "type": "access"})
        token = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        if not data['session_id']:
            raise ValueError("ID сессии не найден")
        
        await redis.set(
            f"token:access:{data['id']}:{data['session_id']}",
            token,
            ex=int(self.access_token_expire.total_seconds())
        )
        return token

    # Создание refresh токена
    async def create_refresh_token(self, data: Dict[str, Any], redis: Redis) -> str:
        """
        Создание `refresh` токена с сохранением в Redis
        :param `data`: Данные пользователя
        :param `redis`: Redis клиент
        :return: Refresh токен
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + self.refresh_token_expire
        to_encode.update({"exp": expire, "type": "refresh"})
        token = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        if not data['session_id']:
            raise ValueError("ID сессии не найден")
        
        await redis.set(
            f"token:refresh:{data['id']}:{data['session_id']}",
            token,
            ex=int(self.refresh_token_expire.total_seconds())
        )
        return token

    # Создание пары токенов
    async def create_tokens(self, user_data: Dict[str, Any], redis: Redis) -> Tuple[str, str]:
        """
        Создание пары токенов
        :param `user_data`: Данные пользователя
        :param `redis`: Redis клиент
        :return: Кортеж из access и refresh токенов
        """
        access_token = await self.create_access_token(user_data, redis)
        refresh_token = await self.create_refresh_token(user_data, redis)
        return access_token, refresh_token

    # Проверка JWT токена
    async def verify_token(self, token: str, token_type: str, redis: Redis) -> Dict[str, Any]:
        """
        Проверка токена с использованием Redis
        :param `token`: JWT токен
        :param `token_type`: Тип токена (`access` или `refresh`)
        :param `redis`: Redis клиент
        :return: Данные пользователя
        """
        from fastapi import HTTPException, status

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось проверить учетные данные",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: Optional[str] = payload.get("id")
            token_type_payload: Optional[str] = payload.get("type")
            session_id: Optional[str] = payload.get("session_id")

            if user_id is None or session_id is None:
                raise credentials_exception

            if token_type != token_type_payload:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный тип токена")
            
            redis_key = f"token:{token_type_payload}:{user_id}:{session_id}"
            stored_data = await redis.get(redis_key)
            
            if stored_data is None:
                raise credentials_exception

            if stored_data != token:
                raise credentials_exception # Токен отозван или истек в Redis
            
            return payload
        
        except JWTError:
            raise credentials_exception
        except Exception as err:
            logger.error(f"Ошибка при проверке токена: {err}")
            raise credentials_exception

    # Установка refresh токена в cookie
    async def set_refresh_token_cookie(self, response: Response, token: str) -> None:
        """
        Установка `refresh` токена в `HttpOnly cookie`
        :param `response`: Response объект
        :param `token`: `Refresh` токен
        """
        response.set_cookie(
            key=self.refresh_cookie_name,
            value=token,
            httponly=True,
            secure=isinstance(self.settings, ProductionSettings) and self.settings.SESSION_COOKIE_SECURE,
            samesite="lax",
            max_age=int(self.refresh_token_expire.total_seconds()),
            path="/api",
        )

    # Установка access токена в cookie
    async def set_access_token_cookie(self, response: Response, token: str) -> None:
        """
        Установка `access` токена в `HttpOnly cookie`
        :param `response`: Response объект
        :param `token`: `Access` токен
        """
        response.set_cookie(
            key=self.access_cookie_name,
            value=token,
            httponly=True,
            secure=isinstance(self.settings, ProductionSettings) and self.settings.SESSION_COOKIE_SECURE,
            samesite="lax",
            max_age=int(self.access_token_expire.total_seconds()),
            path="/api",
        )

    # Отзыв токенов пользователя
    async def revoke_tokens(self, user_id: str, redis: Redis, session_id: Optional[str] = None) -> None:
        """
        Отзыв токенов пользователя удалением из Redis
        :param `user_id`: ID пользователя
        :param `redis`: Redis клиент
        :param `session_id`: ID сессии (если None, отзываются все токены пользователя)
        """
        if session_id:
            access_key = f"token:access:{user_id}:{session_id}"
            refresh_key = f"token:refresh:{user_id}:{session_id}"
            await redis.delete(access_key, refresh_key)
        else:
            access_keys = await redis.keys(f"token:access:{user_id}:*")
            refresh_keys = await redis.keys(f"token:refresh:{user_id}:*")
            
            if access_keys:
                await redis.delete(*access_keys)
            if refresh_keys:
                await redis.delete(*refresh_keys)

jwt_handler = JWTHandler(settings)

# Зависимость для получения текущего пользователя из токена
async def get_current_user_payload(
    request: Request,
    redis: Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """
    Декодирует токен и возвращает `payload`
    :param `token`: JWT токен
    :param `settings`: Настройки приложения
    :param `redis`: Redis клиент
    :return: Данные пользователя
    """
    token = request.cookies.get(jwt_handler.access_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Нет access токена")
    
    payload = await jwt_handler.verify_token(token, "access", redis)
    return payload

# Зависимость для получения текущего активного пользователя
async def get_current_active_user(
    payload: Dict[str, Any] = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Получает `payload`, находит пользователя в БД и проверяет активность аккаунта
    :param `payload`: Данные пользователя
    :param `db`: AsyncSession
    :return: Пользователь
    """
    from core.models.user import User
    from sqlalchemy import select

    user_id_str = payload.get("id")
    if user_id_str is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный токен: некорректный ID пользователя")

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Неактивный пользователь")
    return user
