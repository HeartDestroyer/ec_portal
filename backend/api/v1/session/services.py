from datetime import datetime, timedelta
import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional, Tuple
from fastapi import Request
import aiohttp

from api.v1.dependencies import settings

# Модели и схемы
from core.models.user import User
from core.models.session import Session
from .schemas import SessionFilter, SessionsPage
from core.extensions.logger import logger

# Утилиты безопасности
from core.security.jwt import JWTHandler

# Сервис для работы с сессиями
class SessionService:
    """
    Сервис для работы с сессиями пользователей

    :`get_location_by_ip`: - Получение геолокации по IP-адресу
    :`user_agent_info`: - Парсинг `User-Agent` для получения информации о браузере и устройстве и геолокации
    :`update_session_activity`: - Обновление времени последней активности сессии
    :`check_session_validity`: - Проверка валидности сессии
    :`create_session`: - Создание новой сессии для пользователя
    :`get_sessions`: - Получение всех активных сессий пользователей для администратора или получение своих сессий пользователем
    :`deactivate_session`: - Завершение конкретной сессии
    :`terminate_other_sessions`: - Завершение всех сессий пользователя кроме текущей
    :`get_session_info`: - Получение подробной информации о сессии
    :`get_active_sessions_count`: - Получение количества активных сессий пользователя
    :`deactivate_all_sessions`: - Деактивация всех сессий пользователя
    """

    # Инициализация
    def __init__(self, db: AsyncSession, jwt_handler: JWTHandler):
        self.db = db
        self.jwt_handler = jwt_handler
        self.redis = None

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
                async with session.get(f"http://ip-api.com/json/{ip_address}?lang=ru") as response:
                    if response.status == 200:
                        data = await response.json()
                        country = data.get("country", "")
                        city = data.get("city", "")
                        region = data.get("regionName", "")
                        
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
            browser = "Yandex"
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
    async def create_session(self, user: User, device: str, browser: Optional[str] = None, ip_address: Optional[str] = None, os: Optional[str] = None, platform: Optional[str] = None, location: Optional[str] = None ) -> Session:
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


    # Получение всех активных сессий пользователей для администратора или получение сессий пользователя
    async def get_sessions(self, filter: SessionFilter, current_session_id: str) -> SessionsPage:
        """
        Получение всех активных сессий пользователей для администратора или получение сессий пользователя
        :param `filter`: Фильтр для сессий
        :param `current_session_id`: ID текущей сессии
        :return: Объект `SessionsPage` с сессиями
        """
        query = select(Session).join(User)

        # Применяем фильтры
        conditions = []
        if filter.is_active is not None:
            conditions.append(Session.is_active == filter.is_active)
        if filter.user_id is not None:
            conditions.append(Session.user_id == filter.user_id)
        if filter.user_name is not None:
            conditions.append(User.name.ilike(f"%{filter.user_name}%"))

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Session.last_activity.desc())

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        query = query.offset((filter.page - 1) * filter.page_size).limit(filter.page_size)

        result = await self.db.execute(query)
        sessions = result.scalars().all()

        for session in sessions:
            if session.last_activity:
                session.last_activity = session.last_activity + timedelta(hours=5)
            if session.created_at:
                session.created_at = session.created_at + timedelta(hours=5)
            if session.user_id:
                user_name = await self.db.get(User, session.user_id)
                if user_name:
                    session.user_name = user_name.name
                    session.is_current = str(session.id) == current_session_id
        
        return SessionsPage(
            total=total,
            page=filter.page,
            page_size=filter.page_size,
            sessions=sessions
        )


    # Завершение конкретной сессии
    async def deactivate_session(self, session_id: str, user_id: str, user_role: str) -> None:
        """
        Завершение конкретной сессии
        :param `session_id`: ID сессии
        :param `user_id`: ID пользователя
        :param `user_role`: Роль пользователя
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
            
            # Проверяем права на завершение сессии
            if user_role not in settings.ADMIN_ROLES and session.user_id != user_uuid:
                logger.warning(f"Сессия {session_id} не принадлежит пользователю {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет прав на завершение этой сессии"
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
