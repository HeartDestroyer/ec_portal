# backend/core/security/jwt_service.py - Сервис для работы с JWT токенами

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis

from core.config.config import settings
from core.extensions.redis import get_redis
from core.extensions.logger import logger
from api.v1.schemas import TokenPayload, Tokens

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

class JWTService:
    """
    Класс для работы с JWT токенами по принципам SOLID, DRY, KISS
    
    Методы для работы с JWT токенами:
        - `create_token` - Создает JWT токен и сохраняет в Redis
        - `create_tokens` - Создает пару access и refresh токенов
        - `verify_token` - Проверяет JWT токен
        - `revoke_tokens` - Отзывает токены пользователя
        - `add_to_blacklist` - Добавляет refresh токен в черный список на время его действия
        - `decode_token` - Декодирует токен без проверки подписи и срока действия (Для обработки в случае ошибки)
        - `set_token_cookie` - Установка токена в HttpOnly cookie
    
    Методы для работы с токенами для верификации и сброса пароля:
        - `create_verification_token` - Создает токен для подтверждения почты
        - `create_reset_token` - Создает токен для сброса пароля
        - `decode_verification_token` - Декодирует токен для подтверждения почты
        - `decode_reset_token` - Декодирует токен для сброса пароля
        
    Зависимости:
        - `get_current_user_payload` - Получает TokenPayload из cookies
    """
    
    def __init__(self):
        # Основные настройки JWT
        self.algorithm = settings.JWT_ALGORITHM
        self.secret_key = settings.JWT_SECRET_KEY
        self.secret_key_signed_url = settings.SECRET_KEY_SIGNED_URL

        # Время жизни токенов
        self.access_token_expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        self.refresh_token_expire = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        # Настройки cookie
        self.refresh_cookie_name = settings.REFRESH_TOKEN_COOKIE
        self.access_cookie_name = settings.ACCESS_TOKEN_COOKIE
        self.secure = settings.SESSION_COOKIE_SECURE

        # Настройки сроков действия токенов и типов для верификации и сброса пароля
        self.email_verification = "email_verification"
        self.password_reset = "password_reset"
        self.time_delta_verification = timedelta(hours=24)
        self.time_delta_reset = timedelta(hours=1)
        self.time_delta_welcome = timedelta(hours=1)
        self.time_delta_notification = timedelta(hours=1)

        # Стандартная ошибка аутентификации
        self.credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось проверить учетные данные",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def _create_token_payload(self, token_data: TokenPayload, token_type: str, expire_delta: timedelta) -> Dict[str, Any]:
        """
        Создает payload для JWT токена\n
        `token_data` - Данные для аутентификации в виде TokenPayload\n
        `token_type` - Тип токена access / refresh\n
        `expire_delta` - Время жизни токена\n
        Возвращает payload токена в виде словаря
        """
        expire = datetime.utcnow() + expire_delta
        return {
            "user_id": str(token_data.user_id),
            "session_id": str(token_data.session_id),
            "role": token_data.role,
            "token_type": token_type,
            "exp": int(expire.timestamp()), 
        }

    def _encode_jwt(self, payload: Dict[str, Any]) -> str:
        """
        Кодирует JWT токен\n
        `payload` - Данные для кодирования в виде словаря\n
        Возвращает JWT токен в виде строки
        """
        try:
            return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        except Exception as err:
            logger.error(f"[encode_jwt] Ошибка кодирования JWT: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка создания токена")

    def _decode_jwt(self, token: str, verify_exp: bool = True) -> Dict[str, Any]:
        """
        Декодирует JWT токен\n
        `token` - JWT токен\n
        `verify_exp` - Флаг для проверки срока действия токена\n
        Возвращает декодированные данные токена в виде словаря
        """
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": verify_exp})
        except JWTError as err:
            logger.error(f"[decode_jwt] Ошибка декодирования JWT: {err}")
            raise self.credentials_exception

    async def _save_token_to_redis(self, token_data: TokenPayload, token: str, token_type: str, expire_delta: timedelta, redis: Redis) -> None:
        """
        Сохраняет новый токен в Redis, а старый удаляет\n
        `token_data` - Данные для аутентификации в виде TokenPayload\n
        `token` - JWT токен\n
        `token_type` - Тип токена access / refresh\n
        `expire_delta` - Время жизни токена
        """
        token_key = f"token:{token_type}:{token_data.user_id}:{token_data.session_id}"
        
        await redis.delete(token_key)
        success = await redis.set(token_key, token, ex=int(expire_delta.total_seconds()))
        if not success:
            logger.error(f"[save_token_to_redis] Ошибка сохранения токена в Redis: {token_key}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка сохранения токена")

    def _validate_required_fields(self, payload: Dict[str, Any]) -> None:
        """
        Проверяет обязательные поля в токене\n
        `payload` - Данные для проверки в виде словаря\n
        В случае ошибки возвращает HTTPException
        """
        required_fields = ["user_id", "session_id", "token_type", "exp", "role"]
        missing_fields = [field for field in required_fields if not payload.get(field)]
        
        if missing_fields:
            logger.error(f"[validate_required_fields] Отсутствуют обязательные поля в токене: {missing_fields}")
            raise self.credentials_exception

    def _check_token_expiration(self, payload: Dict[str, Any]) -> None:
        """
        Проверяет срок действия токена\n
        `payload` - Данные для проверки в виде словаря\n
        В случае ошибки возвращает HTTPException
        """
        current_time = datetime.utcnow().timestamp()
        exp = payload.get("exp")
        
        if current_time > exp:
            minutes_expired = int((current_time - exp) / 60)
            logger.warning(f"[check_token_expiration] Токен истек {minutes_expired} минут назад")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Токен истек {minutes_expired} минут назад")

    def _verify_token_type(self, payload: Dict[str, Any], expected_type: str) -> None:
        """
        Проверяет тип токена\n
        `payload` - Данные для проверки в виде словаря\n
        `expected_type` - Ожидаемый тип токена\n
        В случае ошибки возвращает HTTPException
        """
        token_type = payload.get("token_type")
        if token_type != expected_type:
            logger.error(f"[verify_token_type] Неверный тип токена: ожидался {expected_type}, получен {token_type}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный тип токена")

    async def _verify_token_in_redis(self, payload: Dict[str, Any], token: str, token_type: str, redis: Redis) -> None:
        """
        Проверяет наличие токена в Redis и соответствие токенов\n
        `payload` - Данные для проверки в виде словаря\n
        `token` - JWT токен\n
        `token_type` - Тип токена\n
        В случае ошибки возвращает HTTPException
        """
        user_id = payload["user_id"]
        session_id = payload["session_id"]
        token_key = f"token:{token_type}:{user_id}:{session_id}"

        # Проверяем наличие токена в Redis
        stored_token = await redis.get(token_key)
        if not stored_token:
            logger.error(f"[verify_token_in_redis] Токен отсутствует в Redis: {token_key}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Токен отсутствует")

        # Проверяем совпадение токенов
        stored_token_str = stored_token.decode('utf-8') if isinstance(stored_token, bytes) else stored_token
        if stored_token_str != token:
            logger.error(f"[verify_token_in_redis] Токен не соответствует сохраненному: {token_key}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Токен не соответствует")

    async def _check_token_blacklist(self, token: str, redis: Redis) -> None:
        """
        Проверяет, находится ли токен в черном списке\n
        `token` - JWT токен\n
        В случае ошибки возвращает HTTPException
        """
        blacklist_key = f"token:blacklist:{token}"
        if await redis.exists(blacklist_key):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Токен в черном списке")


    async def create_token(self, token_data: TokenPayload, token_type: str, redis: Redis) -> str:
        """
        Создает JWT токен и сохраняет в Redis\n
        `token_data` - Данные для аутентификации в виде TokenPayload\n
        `token_type` - Тип токена access / refresh\n
        Возвращает созданный токен, в случае ошибки возвращает HTTPException
        """
        try:
            expire_delta = self.access_token_expire if token_type == "access" else self.refresh_token_expire

            # Создаем payload и кодируем токен
            payload = self._create_token_payload(token_data, token_type, expire_delta)
            token = self._encode_jwt(payload)

            # Сохраняем в Redis
            await self._save_token_to_redis(token_data, token, token_type, expire_delta, redis)
            
            logger.debug(f"[create_token] Токен {token_type} создан для пользователя {token_data.user_id}")
            return token

        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"[create_token] Ошибка при создании {token_type} токена: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при создании токена")

    async def create_tokens(self, token_data: TokenPayload, redis: Redis) -> Tokens:
        """
        Создает пару access и refresh токенов\n
        `token_data` - Данные для аутентификации в виде TokenPayload\n
        Возвращает объект Tokens с токенами, в случае ошибки возвращает HTTPException
        """
        try:
            access_token = await self.create_token(token_data, "access", redis)
            refresh_token = await self.create_token(token_data, "refresh", redis)
            
            return Tokens(
                access_token=access_token,
                refresh_token=refresh_token
            )
        
        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"[create_tokens] Ошибка при создании пары токенов: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка создания пары токенов")

    async def verify_token(self, token: str, token_type: str, redis: Redis) -> TokenPayload:
        """
        Проверяет JWT токен\n
        `token` - JWT токен\n
        `token_type` - Тип токена access / refresh\n
        Возвращает данные токена в виде TokenPayload, в случае ошибки возвращает HTTPException
        """
        try:
            payload = self._decode_jwt(token, verify_exp=False)                     # Декодируем токен
            self._validate_required_fields(payload)                                 # Проверяем обязательные поля
            self._verify_token_type(payload, token_type)                            # Проверяем тип токена
            self._check_token_expiration(payload)                                   # Проверяем срок действия
            await self._check_token_blacklist(token, redis)                         # Проверяем черный список
            await self._verify_token_in_redis(payload, token, token_type, redis)    # Проверяет наличие токена в Redis и соответствие токенов
            return TokenPayload.factory.create_from_dict(payload)                   # Создаем TokenPayload
            
        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"[verify_token] Ошибка при проверке токена: {err}")
            raise self.credentials_exception

    async def revoke_tokens(self, user_id: str, redis: Redis, session_id: Optional[str] = None, token_type: Optional[str] = None) -> bool:
        """
        Отзывает токены пользователя\n
        `user_id` - ID пользователя\n
        `session_id` - ID сессии\n
        `token_type` - Тип токена\n
        Возвращает True в случае успешного отзыва, в противном случае False
        """
        try:
            pattern_parts = [
                "token",
                token_type or "*",
                user_id,
                session_id or "*"
            ]
            pattern = ":".join(pattern_parts)
            
            keys = await redis.keys(pattern)
            if not keys:
                logger.info(f"[revoke_tokens] Токены для отзыва не найдены: {pattern}")
                return False
            
            await redis.delete(*keys)
            logger.info(f"[revoke_tokens] Отозвано {len(keys)} токенов")
            return True
            
        except Exception as err:
            logger.error(f"[revoke_tokens] Ошибка отзыва токенов: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка отзыва токенов")

    async def add_to_blacklist(self, token: str, redis: Redis) -> None:
        """Добавляет refresh токен в черный список на время его действия\n
        `token` - JWT токен
        """
        try:
            payload = self._decode_jwt(token, verify_exp=False)
            exp = payload.get("exp")
            now = int(datetime.utcnow().timestamp())
            ttl = exp - now if exp and exp > now else 0
            
            if ttl > 0:
                blacklist_key = f"token:blacklist:{token}"
                await redis.set(blacklist_key, token, ex=ttl)
                logger.debug(f"[add_to_blacklist] Токен добавлен в черный список с TTL {ttl}s")
            else:
                logger.warning("[add_to_blacklist] Токен истек и не добавлен в черный список")
                
        except Exception as err:
            logger.error(f"[add_to_blacklist] Ошибка добавления токена в черный список: {err}")

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

    async def set_token_cookie(self, response: Response, token: str, token_type: str) -> None:
        """
        Установка токена в HttpOnly cookie\n
        `token` - Токен\n
        `token_type` - Тип токена access / refresh\n
        В случае ошибки возвращает HTTPException
        """
        cookie_config = {
            "access": (self.access_cookie_name, self.access_token_expire),
            "refresh": (self.refresh_cookie_name, self.refresh_token_expire)
        }

        cookie_name, expire_delta = cookie_config[token_type]
        
        response.set_cookie(
            key=cookie_name,
            value=token,
            httponly=True,
            secure=self.secure,
            samesite="lax",
            max_age=int(expire_delta.total_seconds()),
            path="/api",
        )


    # Токены для верификации и сброса пароля

    def create_verification_token(self, user_id: str) -> str:
        """
        Создает токен для подтверждения почты\n
        `user_id` - ID пользователя\n
        Возвращает JWT токен, в случае ошибки возвращает HTTPException
        """
        try:
            expire = datetime.utcnow() + self.time_delta_verification
            payload = {
                "user_id": user_id,
                "exp": int(expire.timestamp()),
                "type": self.email_verification,
            }
            return jwt.encode(payload, self.secret_key_signed_url, algorithm=self.algorithm)
        except Exception as err:
            logger.error(f"[create_verification_token] Ошибка при создании токена верификации: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при создании токена верификации")

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
                "type": self.password_reset,
            }
            return jwt.encode(payload, self.secret_key_signed_url, algorithm=self.algorithm)
        except Exception as err:
            logger.error(f"[create_reset_token] Ошибка при создании токена сброса пароля: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при создании токена сброса пароля")

    def decode_verification_token(self, token: str) -> dict:
        """
        Декодирует токен для подтверждения почты\n
        `token` - JWT токен для верификации\n
        Возвращает данные токена без проверки через Redis, в случае ошибки возвращает HTTPException
        """
        try:
            payload = jwt.decode(token, self.secret_key_signed_url, algorithms=[self.algorithm])

            # Проверка типа токена
            if payload.get("type") != self.email_verification:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный тип токена")
                
            # Проверка срока действия
            exp = payload.get("exp")
            if exp and datetime.utcnow().timestamp() > exp:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Срок действия токена истек")
                
            return payload
        except JWTError as err:
            logger.error(f"[decode_verification_token] Ошибка при декодировании токена подтверждения почты: {err}")
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
            if payload.get("type") != self.password_reset:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный тип токена")
                
            # Проверка срока действия
            exp = payload.get("exp")
            if exp and datetime.utcnow().timestamp() > exp:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Срок действия токена истек")
                
            return payload
        except JWTError as err:
            logger.error(f"[decode_reset_token] Ошибка при декодировании токена сброса пароля: {err}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недействительный токен сброса пароля")

jwt_service = JWTService()


async def get_current_user_payload(
    request: Request, 
    redis: Redis = Depends(get_redis)
) -> TokenPayload:
    """
    Декодирует токен и возвращает TokenPayload\n
    В случае ошибки возвращает HTTPException
    """
    try:
        access_token = request.cookies.get(jwt_service.access_cookie_name)
        if not access_token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                access_token = auth_header.replace("Bearer ", "")
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Токен отсутствует",
                    headers={"WWW-Authenticate": "Bearer"}
                )
        
        payload = await jwt_service.verify_token(access_token, "access", redis)    
        return payload
    
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[get_current_user_payload] Ошибка при получении данных пользователя: {err}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ошибка при получении данных пользователя", headers={"WWW-Authenticate": "Bearer"})
