# backend/api/v1/auth/services/two_factor_service.py - Сервис для работы с двухфакторной аутентификацией

# TODO: Запилить двухфакторную аутентификацию
# TODO: Запилить генерацию секретного ключа
# TODO: Запилить проверку TOTP токена

from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import Optional
import pyotp

from core.services.base_service import BaseService
from api.v1.schemas import MessageResponse

class TwoFactorService(BaseService):
    """
    Сервис для работы с двухфакторной аутентификацией

    Методы:
        - `enable_2fa_service()` - Включение двухфакторной аутентификации
        - `disable_2fa_service()` - Выключение двухфакторной аутентификации
        - `verify_2fa_service()` - Проверка двухфакторной аутентификации
    """

    def __init__(self, db: AsyncSession, redis: Optional[Redis]):
        super().__init__(db, redis)

    async def enable_2fa_service(self) -> MessageResponse:
        """
        Включение двухфакторной аутентификации
        """
        return MessageResponse(message="TODO: Запилить двухфакторную аутентификацию")
    
    async def generate_secret(self, user_email: str) -> str:
        """
        Генерация секретного ключа для 2FA\n
        `user_email` - Email пользователя\n
        Возвращает секретный ключ
        """
        return pyotp.random_base32()

    async def verify_totp(self, secret: str, token: str) -> bool:
        """
        Проверка TOTP токена\n
        `secret` - Секретный ключ\n
        `token` - TOTP токен\n
        Возвращает результат проверки
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(token)
