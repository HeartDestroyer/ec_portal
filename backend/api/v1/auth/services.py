from datetime import datetime
import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from redis.asyncio import Redis
from typing import Optional, Tuple, Dict, Any
from fastapi import Request

# Модели и схемы
from core.models.user import User
from .schemas import UserCreate, ResetPassword, UserLogin
from core.extensions.logger import logger

# Сервисы и зависимости
from api.v1.session.services import SessionService

# Утилиты безопасности
from core.security.password import password_manager
from core.security.jwt import JWTHandler
from core.security.email import EmailManager
from utils.functions import format_phone_number

# Сервис для аутентификации пользователя
class AuthenticationService:
    """
    Сервис для аутентификации пользователя

    :`get_user_by_login_or_email`: - Получение пользователя по имени или email
    :`register`: - Регистрация пользователя
    :`authenticate_user`: - Аутентификация пользователя
    :`refresh_access_token`: - Обновление токенов
    :`logout`: - Выход из системы
    :`request_password_reset_service`: - Запрос на сброс пароля
    :`reset_password_service`: - Сброс пароля
    :`verify_email_token`: - Верификация `email` пользователя, в случае успеха верифицирует и активирует пользователя
    :`request_email_verification`: - Запрос на подтверждение `email`
    """

    # Инициализация
    def __init__(self, db: AsyncSession, redis: Redis, jwt_handler: JWTHandler, email_manager: EmailManager):
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
    async def register(self, user_data: UserCreate) -> Tuple[User, str]:
        """
        Регистрация нового пользователя в таблице `users`
        :param user_data: Данные пользователя для регистрации
        :return: Кортеж из пользователя и сообщения
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

        return new_user, "Письмо для подтверждения отправлено на почту"

    # Аутентификация пользователя
    async def authenticate_user(self, credentials: UserLogin, request: Request) -> Tuple[str, str]:
        """
        Аутентификация пользователя и создание сессии
        :param `credentials`: Данные для входа
        :param `request`: Запрос для получения информации о пользователе
        :return: `access_token`, `refresh_token`
        """
        user = await self.get_user_by_login_or_email(credentials.login_or_email)
        session_service = SessionService(self.db, self.jwt_handler)

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
        
        # Проверка активности аккаунта
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Аккаунт деактивирован, обратитесь к администратору"
            )

        # Проверка пароля
        if not password_manager.verify_password(credentials.password, user.hashed_password):
            await password_manager.handle_failed_login(user)
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверное имя пользователя/email или пароль"
            )

        # Сброс счетчика неудачных попыток и обновление last_login
        await password_manager.reset_failed_attempts(user)
        user.last_login = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)

        browser, os, platform, device, location = await session_service.user_agent_info(request)
        session = await session_service.create_session(
            user=user,
            device=device,
            browser=browser,
            ip_address=request.client.host if request.client else None,
            os=os,
            platform=platform,
            location=location
        )

        # Создание токенов с ID сессии
        user_payload = {
            "id": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "login": user.login,
            "session_id": str(session.id)
        }
        access_token, refresh_token = await self.jwt_handler.create_tokens(user_payload, self.redis)

        return access_token, refresh_token

    # Обновление токенов
    async def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        """
        Обновляет `access` и `refresh` токены
        :param `refresh_token`: Refresh токен
        :return: Кортеж из `access` токена и `refresh` токена
        """
        # Проверка refresh токена
        payload = await self.jwt_handler.verify_token(refresh_token, "refresh", self.redis)
        session_service = SessionService(self.db, self.jwt_handler)

        # Получение пользователя
        user_id = uuid.UUID(payload["id"])
        session_id = uuid.UUID(payload["session_id"])
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            await self.jwt_handler.revoke_tokens(str(user_id), self.redis, str(session_id))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный refresh токен или пользователь неактивен"
            )

        if session_id:
            if not await session_service.check_session_validity(str(session_id)):
                await self.jwt_handler.revoke_tokens(str(user_id), self.redis, str(session_id))
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Сессия истекла или неактивна"
                )

        # Отзыв старых токенов текущей сессии (обязательно перед созданием новых)
        await self.jwt_handler.revoke_tokens(str(user_id), self.redis, str(session_id))

        # Создание новых токенов с ID сессии
        user_payload = {
            "id": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "login": user.login,
            "session_id": str(session_id)
        }
        new_access_token, new_refresh_token = await self.jwt_handler.create_tokens(user_payload, self.redis)

        return new_access_token, new_refresh_token

    # Выход из системы
    async def logout(self, payload: Dict[str, Any]) -> Tuple[str, str]:
        """
        Выход из системы
        :param `payload`: Данные пользователя
        :return: Кортеж из `user_id` и `session_id`
        """
        try:
            user_id = str(payload.get("id"))
            session_id = str(payload.get("session_id"))
            user_role = str(payload.get("role"))

            if not user_id or not session_id:
                raise HTTPException(status_code=400, detail="Неверные данные пользователя")

            # Проверяем, что это валидные UUID
            uuid.UUID(user_id)
            uuid.UUID(session_id)

            # Отзыв токенов только для текущей сессии
            await self.jwt_handler.revoke_tokens(user_id, self.redis, session_id)

            try:
                # Пытаемся деактивировать сессию, если она существует
                session_service = SessionService(self.db, self.jwt_handler)
                await session_service.deactivate_session(session_id, user_id, user_role)
            except HTTPException as err:
                if err.status_code == 404:
                    logger.info(f"Сессия {session_id} не найдена при выходе пользователя {user_id}")
                else:
                    raise

            return user_id, session_id
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат ID")
        except Exception as err:
            logger.error(f"Ошибка при выходе из системы: {err}")
            raise HTTPException(status_code=500, detail="Ошибка при выходе из системы")
    
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
        Сброс `password` пользователя по `токену` из `email` и отзыв всех активных сессий пользователя
        :param `data`: Данные для сброса пароля `token`, `new_password`
        """
        if not self.email_manager:
            raise HTTPException(status_code=500, detail="Сервис Email не настроен")
        payload = self.email_manager.verify_token(data.token, "password_reset")
        if not payload:
            raise HTTPException(status_code=400, detail="Невалидный или просроченный токен")

        # Получение пользователя
        user_id = uuid.UUID(payload["id"])
        session_id = uuid.UUID(payload["session_id"])
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        if not session_id:
            raise HTTPException(status_code=400, detail="Сессия пользователя не найдена")

        # Обновляем пароль
        user.hashed_password = password_manager.hash_password(data.new_password)
        # Сбрасываем блокировку, если была
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.db.commit()

        # Отзываем все токены пользователя после сброса пароля
        await self.jwt_handler.revoke_tokens(str(user.id), self.redis)

        # Деактивация всех сессий пользователя
        session_service = SessionService(self.db, self.jwt_handler)
        await session_service.deactivate_all_sessions(str(user.id))

    # Верификация email
    async def verify_email_token(self, token: str) -> User:
        """
        Верификация `email` пользователя, в случае успеха верифицирует и активирует пользователя
        :param `token`: `Токен` для верификации
        :return: Пользователь
        """
        if not self.email_manager:
            raise HTTPException(status_code=500, detail="Сервис Email не настроен")
        payload = self.email_manager.verify_token(token, "email_verification")
        if not payload:
            raise HTTPException(status_code=400, detail="Невалидный или просроченный токен")

        user_id = uuid.UUID(payload["id"])
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

    # Запрос на подтверждение email
    async def request_email_verification(self, user: User):
        """
        Запрос на подтверждение `email`
        :param `user`: Пользователь
        """
        if not self.email_manager:
            raise HTTPException(status_code=500, detail="Cервис Email не настроен")
        if user.is_verified:
            raise HTTPException(status_code=400, detail="Почта уже подтверждена")
        await self.email_manager.send_verification_email(user.email, user.id)
