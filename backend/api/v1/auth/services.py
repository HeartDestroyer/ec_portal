# backend/api/auth/services.py

from datetime import datetime, timedelta
import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from redis.asyncio import Redis
from typing import Optional, Tuple, List, Dict, Any
from fastapi import Request
import aiohttp

# Модели и схемы
from core.models.user import User
from core.models.session import Session
from .schemas import UserCreate, ResetPassword, UserLogin
from core.extensions.logger import logger

# Утилиты безопасности
from core.security.password import password_manager
from core.security.jwt import JWTHandler
from core.security.email import EmailManager
from utils.functions import format_phone_number

# Сервис для аутентификации пользователя
class AuthenticationService:
    """
    Сервис для аутентификации пользователя
    """

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

    # Получение геолокации по IP-адресу
    async def get_location_by_ip(self, ip_address: str) -> str:
        """
        Получение геолокации по IP-адресу
        :param `ip_address`: IP-адрес
        :return: Строка с информацией о местоположении
        """
        if not ip_address:
            return "Локальная сеть"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://ipapi.co/{ip_address}/json/") as response:
                    if response.status == 200:
                        data = await response.json()
                        country = data.get("country_name", "")
                        city = data.get("city", "")
                        region = data.get("region", "")
                        
                        # Формируем строку с местоположением
                        location_parts = []
                        if city:
                            location_parts.append(city)
                        if region and region != city:
                            location_parts.append(region)
                        if country:
                            location_parts.append(country)
                        
                        return ", ".join(location_parts) if location_parts else "Неизвестное местоположение"
                    return "Неизвестное местоположение"
        except Exception as err:
            logger.error(f"Ошибка при получении геолокации: {err}")
            return "Неизвестное местоположение"

    # Парсинг `User-Agent` для получения информации о браузере и устройстве и геолокации
    async def user_agent_info(self, request: Request) -> Tuple[str, str, str, str, str]:
        """
        Парсинг `User-Agent` для получения информации о браузере и устройстве и геолокации
        :param `request`: Запрос для получения информации о пользователе
        :return: Кортеж из `browser`, `os`, `platform`, `device`, `location`
        """
        user_agent = request.headers.get("User-Agent", "")
        
        ip_address = None
        if request.client:
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                ip_address = forwarded_for.split(",")[0].strip()
            else:
                ip_address = request.client.host
            
            if ip_address in ("127.0.0.1", "localhost", "::1"):
                ip_address = "127.0.0.1"
        
        browser = None
        os = None
        platform = None
        device = None

        # Определение браузера
        if "Firefox" in user_agent:
            browser = "Mozilla Firefox"
        elif "YaBrowser" in user_agent:
            browser = "Яндекс Браузер"
        elif "Chrome" in user_agent:
            browser = "Google Chrome"
        elif "Safari" in user_agent:
            browser = "Safari"
        elif "Edge" in user_agent:
            browser = "Microsoft Edge"
        elif "Opera" in user_agent:
            browser = "Opera"
        elif "MSIE" in user_agent or "Trident" in user_agent:
            browser = "Internet Explorer"
        else:
            browser = "Нет данных"

        # Определение операционной системы
        if "Windows" in user_agent:
            os = "Windows"
        elif "Mac OS" in user_agent:
            os = "MacOS"
        elif "Linux" in user_agent:
            os = "Linux"
        elif "Android" in user_agent:
            os = "Android"
        elif "iOS" in user_agent:
            os = "iOS"
        else:
            os = "Нет данных"

        # Определение платформы (тип устройства)
        if "Mobile" in user_agent or "Android" in user_agent or "iPhone" in user_agent:
            platform = "Мобильный"
        elif "Tablet" in user_agent or "iPad" in user_agent:
            platform = "Планшет"
        else:
            platform = "Десктоп"

        # Определение конкретного устройства
        if "iPhone" in user_agent:
            device = "iPhone"
        elif "iPad" in user_agent:
            device = "iPad"
        elif "Android" in user_agent:
            if "SM-" in user_agent:
                device = "Samsung Galaxy"
            elif "Pixel" in user_agent:
                device = "Google Pixel"
            elif "OnePlus" in user_agent:
                device = "OnePlus"
            else:
                device = "Android Device"
        elif "Macintosh" in user_agent:
            device = "Mac"
        elif "Windows" in user_agent:
            device = "Windows PC"
        else:
            device = platform.capitalize()  # Используем платформу как устройство по умолчанию

        # Получение геолокации по IP
        location = await self.get_location_by_ip(ip_address) if ip_address else "Локальная сеть"

        return browser, os, platform, device, location

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

        # Парсинг User-Agent для получения информации о браузере и устройстве
        browser, os, platform, device, location = await self.user_agent_info(request)

        # Создание сессии пользователя
        session_service = SessionService(self.db, self.jwt_handler)
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

        # Получение пользователя
        user_id = uuid.UUID(payload["id"])
        session_id = uuid.UUID(payload["session_id"])
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            # Если пользователя нет или неактивен, отзываем токены в Redis
            await self.jwt_handler.revoke_tokens(str(user_id), self.redis, str(session_id))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный refresh токен или пользователь неактивен"
            )

        if session_id:
            session_service = SessionService(self.db, self.jwt_handler)
            if not await session_service.check_session_validity(str(session_id)):
                # Если сессия невалидна, отзываем токены в Redis
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
                await session_service.deactivate_session(session_id, user_id)
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
    
# Сервис для работы с сессиями
class SessionService:
    """
    Сервис для работы с сессиями
    """

    # Инициализация
    def __init__(self, db: AsyncSession, jwt_handler: JWTHandler):
        self.db = db
        self.jwt_handler = jwt_handler

    # Обновление времени последней активности сессии
    async def update_session_activity(self, session_id: str) -> None:
        """
        Обновление времени последней активности `last_activity` сессии
        :param `session_id`: ID сессии
        """
        session = await self.db.get(Session, session_id)
        if session and session.is_active:
            session.last_activity = datetime.utcnow()
            await self.db.commit()

    # Проверка валидности сессии
    async def check_session_validity(self, session_id: str) -> bool:
        """
        Проверка валидности сессии
        :param `session_id`: ID сессии
        :return: True если сессия валидна, False в противном случае
        """
        session = await self.db.get(Session, session_id)
        if not session:
            return False
        
        # Проверяем только активность сессии
        if not session.is_active:
            return False
        
        # Обновляем время последней активности
        await self.update_session_activity(session_id)
        return True

    # Создание новой сессии для пользователя
    async def create_session(
        self, user: User, device: str,
        browser: Optional[str] = None, ip_address: Optional[str] = None,
        os: Optional[str] = None, platform: Optional[str] = None, location: Optional[str] = None
    ) -> Session:
        """
        Создание новой сессии пользователя
        :param `user`: Пользователь
        :param `device`: Информация об устройстве
        :param `browser`: Информация о браузере
        :param `ip_address`: IP-адрес
        :param `os`: Операционная система
        :param `platform`: Платформа (мобильная/десктоп)
        :param `location`: Геолокация
        :return: `Session`
        """
        session = Session(
            user_id=user.id,
            device=device,
            browser=browser,
            ip_address=ip_address,
            os=os,
            platform=platform,
            location=location,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    # Получение всех активных сессий пользователя
    async def get_user_sessions(self, user_id: uuid.UUID, current_session_id: uuid.UUID) -> List[Session]:
        """
        Получение всех активных сессий пользователя
        :param `user_id`: ID пользователя
        :param `current_session_id`: ID текущей сессии
        :return: Список сессий
        """
        query = select(Session).where(
            and_(
                Session.user_id == user_id,
                Session.is_active == True
            )
        ).order_by(Session.last_activity.desc())
        
        result = await self.db.execute(query)
        sessions = result.scalars().all()
        
        # Устанавливаем is_current для текущей сессии и корректируем время
        for session in sessions:
            session.is_current = str(session.id) == str(current_session_id)
            if session.last_activity:
                session.last_activity = session.last_activity + timedelta(hours=5)
        
        return sessions

    # Завершение конкретной сессии
    async def deactivate_session(self, session_id: str, user_id: str) -> None:
        """
        Завершение конкретной сессии
        :param `session_id`: ID сессии
        :param `user_id`: ID пользователя
        """
        try:
            session_uuid = uuid.UUID(session_id)
            user_uuid = uuid.UUID(user_id)
            
            session = await self.db.get(Session, session_uuid)
            
            # Проверяем существование сессии и принадлежность пользователю
            if not session:
                logger.warning(f"Сессия {session_id} не найдена")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Сессия пользователя не найдена"
                )
            
            if session.user_id != user_uuid:
                logger.warning(f"Сессия {session_id} не принадлежит пользователю {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Сессия пользователя не найдена"
                )
            
            # Деактивируем сессию
            session.is_active = False
            await self.db.commit()
            logger.info(f"Сессия {session_id} успешно деактивирована для пользователя {user_id}")
            
        except ValueError as err:
            logger.error(f"Ошибка при обработке UUID: {err}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный формат ID"
            )
        except Exception as err:
            logger.error(f"Ошибка при деактивации сессии: {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при деактивации сессии"
            )

    # Завершение всех сессий пользователя кроме текущей
    async def terminate_other_sessions(self, current_session_id: str, user_id: str) -> None:
        """
        Завершение всех сессий пользователя кроме текущей
        :param `current_session_id`: ID текущей сессии
        :param `user_id`: ID пользователя
        """
        query = select(Session).where(
            and_(
                Session.user_id == user_id,
                Session.id != current_session_id,
                Session.is_active == True
            )
        )

        result = await self.db.execute(query)
        sessions = result.scalars().all()
        
        for session in sessions:
            session.is_active = False
        
        await self.db.commit()


    # Получение подробной информации о сессии
    async def get_session_info(self, session_id: str) -> Optional[dict]:
        """
        Получение подробной информации о сессии
        :param `session_id`: ID сессии
        :return: Словарь с информацией о сессии или None
        """
        session = await self.db.get(Session, session_id)
        if not session:
            return None
        return session.to_dict()

    # Получение количества активных сессий пользователя
    async def get_active_sessions_count(self, user_id: str) -> int:
        """
        Получение количества активных сессий пользователя
        :param `user_id`: ID пользователя
        :return: Количество активных сессий
        """
        query = select(Session).where(
            and_(
                Session.user_id == user_id,
                Session.is_active == True
            )
        )
        result = await self.db.execute(query)
        return len(result.scalars().all())

    # Деактивация всех сессий пользователя
    async def deactivate_all_sessions(self, user_id: str) -> None:
        """
        Деактивация всех сессий пользователя
        :param `user_id`: ID пользователя
        """
        query = select(Session).where(
            and_(
                Session.user_id == user_id,
                Session.is_active == True
            )
        )
        result = await self.db.execute(query)
        sessions = result.scalars().all()
        
        for session in sessions:
            session.is_active = False
        
        await self.db.commit()
