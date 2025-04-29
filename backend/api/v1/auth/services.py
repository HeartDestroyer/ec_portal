# backend/api/auth/services.py

from datetime import datetime
import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from redis.asyncio import Redis
from typing import Optional

# Модели и схемы
from core.models.user import User
from .schemas import UserCreate, ResetPassword
from core.extensions.logger import logger

# Утилиты безопасности
from core.security.password import password_manager
from core.security.jwt import JWTHandler
from core.security.email import EmailManager
from utils.functions import format_phone_number

# Сервис для аутентификации пользователя
class AuthenticationService:
    """Сервис для аутентификации пользователя"""

    # Инициализация
    def __init__(
        self,
        db: AsyncSession,
        redis: Redis,
        jwt_handler: JWTHandler,
        email_manager: EmailManager
    ):
        self.db = db
        self.redis = redis
        self.jwt_handler = jwt_handler
        self.email_manager = email_manager

    # Получение пользователя по имени или email
    async def get_user_by_login_or_email(self, login_or_email: str) -> Optional[User]:
        """
        Находит пользователя по `login` или `email` в таблице `users`
        :param login_or_email: `login` или `email` пользователя
        :return: Пользователь или None
        """
        query = select(User).where(
            or_(User.login == login_or_email, User.email == login_or_email)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    # Регистрация пользователя
    async def register(self, user_data: UserCreate) -> User:
        """
        Регистрация нового пользователя в таблице `users`
        :param user_data: Данные пользователя для регистрации
        :return: Пользователь и сообщение
        """
        existing_user = await self.get_user_by_login_or_email(user_data.login)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким логином уже существует"
            )
        existing_user = await self.get_user_by_login_or_email(user_data.email)
        if existing_user:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует"
            )

        hashed_password = password_manager.hash_password(user_data.password)
        formatted_phone = format_phone_number(user_data.phone) if user_data.phone else None

        new_user = User(
            **user_data.model_dump(exclude={"password", 'phone'}),
            phone=formatted_phone,
            hashed_password=hashed_password,
            is_active=False,
            is_verified=False
        )

        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)

        # Отправка письма для подтверждения
        if self.email_manager:
            try:
                await self.email_manager.send_verification_email(new_user.email, new_user.id)
            except Exception as err:
                logger.error(f"Ошибка в отправке письма для подтверждения {new_user.email}: {err}")

        return new_user, "Письмо для подтверждения отправлено"

    # Аутентификация пользователя
    async def authenticate_user(self, login_or_email: str, password: str) -> tuple[User, str, str]:
        """
        Аутентификация пользователя
        :param login_or_email: `login` или `email` пользователя
        :param password: `password` пользователя
        :return: Кортеж из пользователя, `access токена` и `refresh токена`
        """
        # Поиск пользователя
        user = await self.get_user_by_login_or_email(login_or_email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверное имя пользователя/email или пароль"
            )

        # Проверка блокировки (защита от брутфорса)
        if await password_manager.check_brute_force(user):
             locked_duration = (user.locked_until - datetime.utcnow()).total_seconds()
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Аккаунт временно заблокирован. Попробуйте через {int(locked_duration // 60)} минут"
            )

        # Проверка пароля
        if not password_manager.verify_password(password, user.hashed_password):
            await password_manager.handle_failed_login(user)
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверное имя пользователя/email или пароль"
            )
        
        # Проверка активности аккаунта
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Аккаунт деактивирован"
            )

        # Сброс счетчика неудачных попыток и обновление last_login
        await password_manager.reset_failed_attempts(user)
        user.last_login = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)

        # Создание токенов
        user_payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "login": user.login
        }
        access_token, refresh_token = await self.jwt_handler.create_tokens(user_payload, self.redis)

        return user, access_token, refresh_token

    # Обновление токенов
    async def refresh_access_token(self, refresh_token: str) -> tuple[str, str]:
        """
        Обновляет `access` и `refresh` токены
        :param refresh_token: Refresh токен
        :return: Кортеж из access токена и refresh токена
        """
        # Проверка refresh токена
        payload = await self.jwt_handler.verify_token(refresh_token, "refresh", self.redis)

        # Получение пользователя
        user_id = uuid.UUID(payload["sub"])
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            # Если пользователя нет или неактивен, отзываем токен в Redis
            await self.jwt_handler.revoke_tokens(str(user_id), self.redis)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный refresh токен или пользователь неактивен"
            )

        # Отзыв старых токенов (обязательно перед созданием новых)
        await self.jwt_handler.revoke_tokens(str(user_id), self.redis)

        # Создание новых токенов
        user_payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "login": user.login
        }
        new_access_token, new_refresh_token = await self.jwt_handler.create_tokens(user_payload, self.redis)

        return new_access_token, new_refresh_token

    # Запрос на подтверждение email
    async def request_email_verification(self, user: User):
        """
        Запрос на подтверждение email
        :param user: Пользователь
        """
        if not self.email_manager:
            raise HTTPException(status_code=500, detail="Cервис Email не настроен")
        if user.is_verified:
            raise HTTPException(status_code=400, detail="Почта уже подтверждена")
        await self.email_manager.send_verification_email(user.email, user.id)

    # Верификация email
    async def verify_email_token(self, token: str) -> User:
        """
        Верификация `email` пользователя, в случае успеха верифицирует и активирует пользователя
        :param token: `Токен` для верификации
        :return: Пользователь
        """
        if not self.email_manager:
            raise HTTPException(status_code=500, detail="Сервис Email не настроен")
        payload = self.email_manager.verify_token(token, "email_verification")
        if not payload:
            raise HTTPException(status_code=400, detail="Невалидный или просроченный токен")

        user_id = uuid.UUID(payload["sub"])
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        if user.is_verified:
            raise HTTPException(status_code=400, detail="Почта уже подтверждена")

        user.is_verified = True
        user.is_active = True # Активируем пользователя после подтверждения
        await self.db.commit()
        await self.db.refresh(user)
        return user

    # Запрос на сброс пароля
    async def request_password_reset_service(self, email: str) -> None:
        """
        Запрос на сброс пароля
        :param email: Email пользователя
        """
        if not self.email_manager:
             raise HTTPException(status_code=500, detail="Сервис Email не настроен")
        user = await self.get_user_by_login_or_email(email)
        if user:
            # Всегда возвращаем успех, чтобы не раскрывать существование email
            try:
                await self.email_manager.send_password_reset_email(user.email, user.id)
            except Exception as err:
                logger.error(f"Ошибка в отправке письма для сброса пароля {email}: {err}")

    # Сброс пароля
    async def reset_password_service(self, data: ResetPassword) -> None:
        """
        Сброс `password` пользователя
        :param data: Данные для сброса пароля `token`, `new_password`
        """
        if not self.email_manager:
            raise HTTPException(status_code=500, detail="Сервис Email не настроен")
        payload = self.email_manager.verify_reset_password_token(data.token)
        if not payload:
            raise HTTPException(status_code=400, detail="Невалидный или просроченный токен")

        # Получение пользователя
        user_id = uuid.UUID(payload["sub"])
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Обновляем пароль
        user.hashed_password = password_manager.hash_password(data.new_password)
        # Сбрасываем блокировку, если была
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.db.commit()

        # Отзываем все токены пользователя после сброса пароля
        await self.jwt_handler.revoke_tokens(str(user.id), self.redis)
