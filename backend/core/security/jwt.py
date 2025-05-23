from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
from functools import wraps

from core.config.config import settings
from core.extensions.redis import get_redis, redis_client
from core.extensions.database import get_db 
from core.models.user import User
from core.extensions.logger import logger
from api.v1.schemas import TokenPayload, Tokens

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def synchronized(lock_name: str):
    """
    Декоратор для синхронизации асинхронных методов\n
    Создает блокировку с указанным именем в экземпляре класса\n
    и обеспечивает последовательное выполнение метода\n
    `lock_name` - Имя атрибута блокировки
    """
    def wrapper(func):
        @wraps(func)
        async def inner(self, *args, **kwargs):
            if not hasattr(self, lock_name):
                setattr(self, lock_name, asyncio.Lock())
            lock = getattr(self, lock_name)
            async with lock:
                return await func(self, *args, **kwargs)
        return inner
    return wrapper

class JWTHandler:
    """
    Класс для работы с JWT токенами использует паттерн Singleton\n
    Методы:
        - `decode_token` - Декодирование токена без проверки подписи и срока действия\n
        - `create_token` - Создание токена с сохранением в Redis\n
        - `create_tokens` - Создание пары токенов refresh и access с сохранением в Redis\n
        - `verify_token` - Проверка токена с использованием Redis\n
        - `set_token_cookie` - Установка токена в cookie\n
        - `revoke_tokens` - Отзыв токенов пользователя удалением из Redis\n
        - `set_refresh_token_to_blacklist` - Добавление refresh токена в черный список\n
        - `decode_verification_token` - Декодирование токена для подтверждения email\n
        - `decode_reset_token` - Декодирование токена для сброса пароля\n
        - `create_verification_token` - Создание токена для подтверждения email\n
        - `create_reset_token` - Создание токена для сброса пароля\n
    Зависимости:
        - `get_current_user_payload` - Получение данных пользователя в виде TokenPayload из токена\n
        - `get_current_active_user` - Получение активного пользователя в виде User из токена
    """
    _instance = None
    _lock = asyncio.Lock()  # Общая блокировка для синхронизации
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JWTHandler, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if not self._initialized:
            self.credentials_exception = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Не удалось проверить учетные данные",
                headers={"WWW-Authenticate": "Bearer"},
            )

            self._setup_token_config()
            self._setup_cookie_config()
            self._setup_jwt_config()
            self._setup_time_deltas()

            self.redis_client = redis_client

            # Блокировки для различных операций
            self._create_token_lock = asyncio.Lock()
            self._verify_token_lock = asyncio.Lock()
            self._revoke_token_lock = asyncio.Lock()
            self._set_refresh_token_to_blacklist_lock = asyncio.Lock()
            self._initialized = True

    def _setup_token_config(self) -> None:
        self.access_token_expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        self.refresh_token_expire = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    def _setup_cookie_config(self) -> None:
        self.refresh_cookie_name = settings.REFRESH_TOKEN_COOKIE
        self.access_cookie_name = settings.ACCESS_TOKEN_COOKIE
        self.secure = settings.SESSION_COOKIE_SECURE if hasattr(settings, 'SESSION_COOKIE_SECURE') else True

    def _setup_jwt_config(self) -> None:
        self.algorithm = settings.JWT_ALGORITHM
        self.secret_key = settings.JWT_SECRET_KEY
        self.secret_key_signed_url = settings.SECRET_KEY_SIGNED_URL

    def _setup_time_deltas(self) -> None:
        self.time_delta_verification = timedelta(hours=24)
        self.time_delta_reset = timedelta(hours=1)
        self.time_delta_welcome = timedelta(hours=1)
        self.time_delta_notification = timedelta(hours=1)


    async def decode_token(self, token: str) -> Optional[TokenPayload]:
        """
        Декодирует токен без проверки подписи и срока действия (Для обработки в случае ошибки)\n
        `token` - Токен для декодирования\n
        Возвращает payload токена в виде TokenPayload в случае ошибки возвращает None
        """
        try:
            raw = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_signature": False, "verify_exp": False})
            return TokenPayload.factory.create_from_dict(raw)
        except Exception:
            return None

    @synchronized("_create_token_lock")
    async def create_token(self, token_data: TokenPayload, redis: Redis, token_type: str, expire_delta: timedelta) -> str:
        """
        Создание токена с сохранением в Redis\n
        `token_data` - Данные для аутентификации в виде TokenPayload\n
        `token_type` - Тип токена access / refresh\n
        `expire_delta` - Время жизни токена\n
        Возвращает созданный токен, в случае ошибки возвращает HTTPException
        """
        try:
            to_encode = {
                "user_id": str(token_data.user_id),
                "session_id": str(token_data.session_id),
                "role": token_data.role
            }
                
            # Добавляем время истечения и тип токена
            expire = datetime.utcnow() + expire_delta
            to_encode.update({
                "token_type": token_type,
                "exp": int(expire.timestamp()), 
            })
            
            token = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            token_key = f"token:{token_type}:{token_data.user_id}:{token_data.session_id}"
            
            # Удаляем старый токен если он существует
            old_token = await redis.get(token_key)
            if old_token:
                await redis.delete(token_key)
            
            # success = await redis.set(token_key, token, ex=int(expire_delta.total_seconds()))
            success = await self.redis_client.atomic_set_token(token_key, token, int(expire_delta.total_seconds()))
            if not success:
                logger.error(f"[create_token] Ошибка сохранения токена в Redis: {token_key}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка сохранения токена")
            
            logger.debug(
                f"[create_token] Токен {token_type} создан и сохранен в Redis для пользователя: {token_data.user_id}, "
                f"сессии: {token_data.session_id}, сроком: {expire_delta}"
            )    
            return token
        
        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"[create_token] Ошибка при создании {token_type} токена: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при создании токена")

    async def create_tokens(self, token_data: TokenPayload, redis: Redis) -> Tokens:
        """
        Создание пары токенов refresh и access\n
        `token_data` - Данные для аутентификации в виде TokenPayload\n
        Возвращает объект Tokens с токенами, в случае ошибки возвращает HTTPException
        """
        try:
            refresh_token = await self.create_token(token_data, redis, "refresh", self.refresh_token_expire)
            access_token = await self.create_token(token_data, redis, "access", self.access_token_expire)

            return Tokens(
                access_token=access_token, 
                refresh_token=refresh_token
            )
        
        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"[create_tokens] Ошибка при создании пары токенов: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при создании пары токенов")

    @synchronized("_verify_token_lock")
    async def verify_token(self, token: str, token_type: str, redis: Redis) -> TokenPayload:
        """
        Проверка токена с использованием Redis\n
        `token` - JWT токен\n
        `token_type` - Тип токена access / refresh\n
        Возвращает данные токена в виде TokenPayload, в случае ошибки возвращает HTTPException
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            
            user_id: str = payload.get("user_id")
            session_id: str = payload.get("session_id")
            token_type_payload: str = payload.get("token_type")
            exp: int = payload.get("exp")
            role: str = payload.get("role")

            logger.debug(
                f"[verify_token] Получен токен: {token[:10]}..., user_id: {user_id}, session_id: {session_id}, "
                f"type: {token_type_payload}, exp: {exp}"
            )

            # Проверка наличия обязательных полей
            required_fields = ["user_id", "session_id", "token_type", "exp", "role"]
            missing_fields = [field for field in required_fields if not payload.get(field)]
            if missing_fields:
                logger.error(f"[verify_token] Отсутствуют обязательные поля в токене: {missing_fields}")
                raise self.credentials_exception
            
            token_key = f"token:{token_type}:{user_id}:{session_id}"

            # Проверка срока действия токена
            current_time = datetime.utcnow().timestamp()
            if current_time > exp:
                logger.warning(
                    f"[verify_token] Токен истек и был удален из Redis: {token_key} (истек {int((current_time - exp) / 60)} минут назад, "
                    f"user_id={user_id}, session_id={session_id}, token={token[:10]}...)"
                )
                await redis.delete(token_key)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Токен истек {int((current_time - exp) / 60)} минут назад")
            
            # Проверка типа токена
            if token_type_payload != token_type:
                logger.error(f"[verify_token] Неверный тип токена: ожидался {token_type}, получен {token_type_payload}")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный тип токена")
            
            # Проверка наличия токена в черный список
            if token_type == "refresh":
                await self.set_refresh_token_to_blacklist(token, redis)
            
            stored_token = await redis.get(token_key)
            
            # Проверка наличия токена в Redis
            if not stored_token:
                logger.error(
                    f"[verify_token] Пользователь {user_id} не имеет токена {token_type} в Redis: {token_key}, "
                    f"Данные из Redis: {stored_token}"
                )
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Токен отсутствует")
            
            # Проверка, что токены совпадают
            stored_token_str = stored_token.decode('utf-8') if isinstance(stored_token, bytes) else stored_token
            if stored_token_str != token:
                logger.error(f"[verify_token] Токен не соответствует сохраненному: {token_key}")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Токен не соответствует")
            
            try:
                payload_copy = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "token_type": token_type,
                    "exp": exp,
                    "role": role
                }
                
                return TokenPayload.factory.create_from_dict(payload_copy)
            
            except Exception as err:
                logger.error(f"[verify_token] Ошибка при создании TokenPayload из словаря: {err}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при обработке токена")
        
        except JWTError as err:
            logger.error(f"[verify_token] Ошибка декодирования JWT: {err}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")
        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"[verify_token] Ошибка при проверке токена: {err}")
            raise self.credentials_exception

    async def set_token_cookie(self, response: Response, token: str, token_type: str) -> None:
        """
        Установка токена в HttpOnly cookie\n
        `token` - Токен\n
        `token_type` - Тип токена self.access_cookie_name или self.refresh_cookie_name\n
        В случае ошибки возвращает HTTPException
        """
        try:
            max_age = int(self.refresh_token_expire.total_seconds())
            if token_type == self.access_cookie_name:
                max_age = int(self.access_token_expire.total_seconds())
                
            response.set_cookie(
                key=token_type,
                value=token,
                httponly=True,
                secure=self.secure,
                samesite="lax",
                max_age=max_age,
                path="/api",
            )

        except Exception as err:
            logger.error(f"[set_token_cookie] Ошибка при установке токена в cookie: {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Ошибка при установке токена в cookie"
            )

    @synchronized("_revoke_token_lock")
    async def revoke_tokens(self, user_id: str, redis: Redis, session_id: Optional[str] = None, token_type: Optional[str] = None) -> bool:
        """
        Отзыв токенов пользователя удалением из Redis\n
        `user_id` - ID пользователя\n
        `session_id` - ID сессии, если None, отзываются все токены пользователя (все токены для всех сессий)\n
        `token_type` - Тип токена для отзыва access / refresh, если None - отзываются оба\n
        Возвращает True если отзыв успешен, иначе False\n
        В случае ошибки возвращает HTTPException
        """
        try:
            parts = [
                "token",
                token_type if token_type else "*",
                user_id,
                session_id if session_id else "*",
            ]
            pattern = ":".join(parts)
            keys = await redis.keys(pattern)
            if not keys:
                logger.info(f"[revoke_tokens] Токены для отзыва не найдены: {pattern}")
                return False
            
            await redis.delete(*keys)
            logger.info(f"[revoke_tokens] Успешно отозвано {len(keys)} токена")
            return True
        
        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"[revoke_tokens] Ошибка при отзыве токенов: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при отзыве токенов")

    @synchronized("_set_refresh_token_to_blacklist_lock")
    async def set_refresh_token_to_blacklist(self, token: str, redis: Redis) -> None:
        """
        Добавление refresh токена в черный список\n
        `token` - JWT токен\n
        """
        try:
            token_key = f"token:blacklist:{token}"
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            exp  = payload.get("exp")
            now = int(datetime.utcnow().timestamp())
            ttl = exp - now if exp and exp > now else 0
            if ttl > 0:
                await redis.set(token_key, token, ex=ttl)
            else:
                logger.warning(f"[set_refresh_token_to_blacklist] Токен истек и не добавлен в черный список: {token_key}")
        except Exception as err:
            logger.error(f"[set_refresh_token_to_blacklist] Ошибка при добавлении токена в черный список: {err}")


    def decode_verification_token(self, token: str) -> dict:
        """
        Декодирует токен для подтверждения email\n
        `token` - JWT токен для верификации\n
        Возвращает данные токена без проверки через Redis, в случае ошибки возвращает HTTPException
        """
        try:
            payload = jwt.decode(token, self.secret_key_signed_url, algorithms=[self.algorithm])
            
            # Проверка типа токена
            if payload.get("type") != "email_verification":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный тип токена")
                
            # Проверка срока действия
            exp = payload.get("exp")
            if exp and datetime.utcnow().timestamp() > exp:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Срок действия токена истек")
                
            return payload
        except JWTError as err:
            logger.error(f"[decode_verification_token] Ошибка при декодировании токена подтверждения email: {err}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недействительный токен подтверждения почты")

    def decode_reset_token(self, token: str) -> dict:
        """
        Декодирует токен для сброса пароля\n
        `token` - JWT токен для сброса пароля\n
        Возвращает данные токена без проверки через Redis, в случае ошибки возвращает HTTPException
        """
        try:
            payload = jwt.decode(token, self.secret_key_signed_url, algorithms=[self.algorithm])
            
            # Проверка типа токена
            if payload.get("type") != "password_reset":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный тип токена")
                
            # Проверка срока действия
            exp = payload.get("exp")
            if exp and datetime.utcnow().timestamp() > exp:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Срок действия токена истек")
                
            return payload
        except JWTError as err:
            logger.error(f"[decode_reset_token] Ошибка при декодировании токена сброса пароля: {err}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недействительный токен сброса пароля")

    def create_verification_token(self, user_id: str) -> str:
        """
        Создает токен для подтверждения email\n
        `user_id` - ID пользователя\n
        Возвращает JWT токен, в случае ошибки возвращает HTTPException
        """
        try:
            expire = datetime.utcnow() + self.time_delta_verification
            payload = {
                "user_id": user_id,
                "exp": int(expire.timestamp()),
                "type": "email_verification",
            }
            return jwt.encode(payload, self.secret_key_signed_url, algorithm=self.algorithm)
        except Exception as err:
            logger.error(f"[create_verification_token] Ошибка при создании токена верификации: {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при создании токена верификации"
            )

    def create_reset_token(self, user_id: str) -> str:
        """
        Создает токен для сброса пароля\n
        `user_id` - ID пользователя\n
        Возвращает JWT токен, в случае ошибки возвращает HTTPException
        """
        try:
            expire = datetime.utcnow() + self.time_delta_reset
            payload = {
                "user_id": user_id,
                "exp": int(expire.timestamp()),
                "type": "password_reset",
            }
            return jwt.encode(payload, self.secret_key_signed_url, algorithm=self.algorithm)
        except Exception as err:
            logger.error(f"[create_reset_token] Ошибка при создании токена сброса пароля: {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при создании токена сброса пароля"
            )

jwt_handler = JWTHandler()

async def get_current_user_payload(
    request: Request, 
    redis: Redis = Depends(get_redis)
) -> TokenPayload:
    """
    Декодирует токен и возвращает TokenPayload\n
    В случае ошибки возвращает HTTPException
    """
    try:
        access_token = request.cookies.get(jwt_handler.access_cookie_name)
        if not access_token:
            # Проверяем наличие токена в заголовке Authorization
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                access_token = auth_header.replace("Bearer ", "")
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Токен отсутствует",
                    headers={"WWW-Authenticate": "Bearer"}
                )
        
        payload = await jwt_handler.verify_token(access_token, "access", redis)    
        return payload
    
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Ошибка при получении данных пользователя: {err}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ошибка при получении данных пользователя",
            headers={"WWW-Authenticate": "Bearer"}
        )

async def get_current_active_user(
    payload: TokenPayload = Depends(get_current_user_payload), 
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Получает TokenPayload, находит пользователя в БД и проверяет активность аккаунта\n
    `payload` - Данные пользователя в виде TokenPayload\n
    Возвращает пользователя в виде User, в случае если пользователь не найден или не активен возвращает HTTPException
    """
    try:
        query = select(User).where(User.id == payload.user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise jwt_handler.credentials_exception
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Аккаунт деактивирован, обратитесь к администратору"
            )
        
        return user
    
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Ошибка при получении пользователя: {err}")
        raise jwt_handler.credentials_exception
