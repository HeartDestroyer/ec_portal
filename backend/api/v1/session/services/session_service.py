# backend/api/v1/session/services/session_service.py - Сервис для работы с сессиями

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from redis.asyncio import Redis
from typing import Optional, List, Any
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

from utils.custom_json_coder import CustomJsonCoder
from backend.core.interfaces.session.session_services import SessionServiceInterface
from core.services.base_service import BaseService
from repositories.session_repository import SessionRepository
from core.models.user import User
from core.models.session import Session
from core.extensions.logger import logger
from core.config.config import settings
from api.v1.session.schemas import SessionFilter, SessionsPage, SessionResponse, UserAgentInfo
from api.v1.session.utils import session_utils

class SessionService(BaseService, SessionServiceInterface):
    """
    Класс для управления сессиями пользователей
    
    Методы:
        - `get_session_by_id` - Получает сессию по ID
        - `get_sessions_user` - Получает все сессии пользователя
        - `get_active_sessions_user` - Получает активные сессии пользователя
        - `create_session` - Создает новую сессию для пользователя
        - `get_sessions_filtered` - Получает список сессий с фильтром и кэшированием
        - `deactivate_session` - Деактивирует сессию
        - `terminate_other_sessions` - Завершает все сессии пользователя, кроме текущей
        - `deactivate_all_sessions` - Деактивирует все сессии пользователя
    """

    def __init__(self, db: AsyncSession, session_repository: SessionRepository, redis: Optional[Redis] = None):
        self.db = db
        self.session_repository = session_repository
        self.redis = redis
        self.admin_roles = settings.ADMIN_ROLES
        self.session_utils = session_utils
        self.max_sessions = settings.MAX_ACTIVE_SESSIONS_PER_USER

    @cache(expire=3600, coder=CustomJsonCoder, namespace="sessions:one")
    async def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """
        Получает сессию по ID и кэширует её\n
        `session_id` - ID сессии\n
        Возвращает сессию, иначе возвращает None
        """
        try:
            return await self.session_repository.get_session_by_id(session_id)
        except Exception as err:
            logger.error(f"Ошибка при получении сессии по ID {session_id}: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при получении сессии по ID")

    @cache(expire=3600, coder=CustomJsonCoder, namespace="sessions:all")
    async def get_sessions_user(self, user_id: str) -> List[Session]:
        """
        Получает все сессии пользователя\n
        `user_id` - ID пользователя\n
        Возвращает список сессий, иначе возвращает пустой список
        """
        try:
            return await self.session_repository.get_sessions_by_user(user_id)
        except Exception as err:
            logger.error(f"Ошибка при получении сессий пользователя {user_id}: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при получении сессий пользователя")

    @cache(expire=3600, coder=CustomJsonCoder, namespace="sessions:active")
    async def get_active_sessions_user(self, user_id: str) -> List[Session]:
        """
        Получает активные сессии пользователя с кэшированием\n
        `user_id` - ID пользователя\n
        Возвращает список активных сессий, иначе возвращает пустой список
        """
        try:
            return await self.session_repository.get_active_sessions_by_user(user_id)
        except Exception as err:
            logger.error(f"Ошибка при получении активных сессий пользователя {user_id}: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при получении активных сессий пользователя")


    async def create_session(self, user: User, user_agent_info: UserAgentInfo) -> Session:
        """
        Создает новую сессию для пользователя\n
        `user` - Пользователь\n
        `user_agent_info` - Информация о браузере пользователя в виде UserAgentInfo\n
        Деактивирует старые сессии, если их количество превышает лимит активных сессий\n
        Возвращает новую сессию, в случае ошибки возвращает HTTPException
        """
        try:
            # Получаем активные сессии
            active_sessions = await self.session_repository.get_active_sessions_by_user(str(user.id))
            
            # Если у пользователя слишком много активных сессий, деактивируем самые старые
            if len(active_sessions) >= self.max_sessions:
                logger.warning(f"Превышен лимит активных сессий ({self.max_sessions}) для пользователя {user.name}")
                sessions_to_deactivate = active_sessions[:(len(active_sessions) - self.max_sessions + 1)]
                for session in sessions_to_deactivate:
                    await self.deactivate_session(str(session.id), str(user.id), user.role.value)
                    await self.jwt_handler.revoke_tokens(str(user.id), self.redis, str(session.id))
                
            # Создаем новую сессию
            new_session = Session(
                user_id=user.id,
                device=user_agent_info.device or "Нет данных",
                browser=user_agent_info.browser or "Нет данных",
                ip_address=user_agent_info.ip_address or "Нет данных",
                os=user_agent_info.os or "Нет данных",
                platform=user_agent_info.platform or "Нет данных",
                location=user_agent_info.location or "Нет данных",
                is_active=True
            )

            self.db.add(new_session)
            await self.db.commit()
            await self.db.refresh(new_session)

            await FastAPICache.clear(f"sessions")
            
            logger.info(f"Создана новая сессия {new_session.id} для пользователя {user.id}")
            return new_session
        
        except Exception as err:
            await self.db.rollback()
            logger.error(f"Ошибка при создании сессии для пользователя {str(user.id)}: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при создании сессии")


    def build_session_query(self, filter: SessionFilter) -> Any:
        """
        Строит запрос для получения сессий (паттерн Builder)\n
        `filter` - Фильтр для сессий\n
        Возвращает построенный SQL-запрос
        """
        query = select(Session)
        conditions = []

        if filter.user_id:
            conditions.append(Session.user_id == filter.user_id)
        if filter.user_name:
            query = query.join(User)
            conditions.append(User.name.ilike(f"%{filter.user_name}%"))
        if filter.is_active is not None:
            conditions.append(Session.is_active == filter.is_active)
        
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(Session.last_activity.desc())

        return query

    @cache(expire=3600, coder=CustomJsonCoder, namespace="sessions:filtered")
    async def get_sessions_filtered(self, filter: SessionFilter, current_session_id: str) -> SessionsPage:
        """
        Получает список сессий с фильтром (паттерн Chain of Responsibility) и кэшированием\n
        `filter` - Фильтр для сессий\n
        `current_session_id` - ID текущей сессии\n
        `current_user_id` - ID текущего пользователя\n
        Возвращает страницу с сессиями, в случае ошибки возвращает HTTPException
        """
        try:
            query = self.build_session_query(filter)
            
            # Вычисляем общее количество результатов для пагинации
            count_query = select(func.count()).select_from(query.subquery())
            total_count_result = await self.db.execute(count_query)
            total_count = total_count_result.scalar() or 0
        
            # Применяем пагинацию
            offset = (filter.page - 1) * filter.page_size
            result = await self.db.execute(query.offset(offset).limit(filter.page_size))
            sessions = result.scalars().all()
            
            # Получаем все необходимые ID пользователей для оптимизации запросов
            user_ids = {str(session.user_id) for session in sessions}
            users_map = {}
            if user_ids:
                users = (await self.db.execute(
                    select(User).where(User.id.in_(user_ids))
                )).scalars().all()
                users_map = {str(user.id): user for user in users}
            
            # Формируем ответы по сессиям
            session_items = []
            for session in sessions:
                user = users_map.get(str(session.user_id))
                user_name = user.name if user else "Нет данных"
                
                session_items.append(SessionResponse(
                    id=str(session.id),
                    user_id=str(session.user_id),
                    user_name=user_name,
                    device=session.device or "Нет данных",
                    browser=session.browser or "Нет данных",
                    os=session.os or "Нет данных",
                    platform=session.platform or "Нет данных",
                    location=session.location or "Нет данных",
                    ip_address=session.ip_address or "Нет данных",
                    last_activity=session.last_activity,
                    created_at=session.created_at,
                    is_active=session.is_active,
                    is_current=str(session.id) == current_session_id,
                ))
            
            total_pages = (total_count + filter.page_size - 1) // filter.page_size if filter.page_size > 0 else 0
            
            page = SessionsPage(
                total=total_count,
                page=filter.page,
                page_size=filter.page_size,
                pages=total_pages,
                sessions=session_items
            )

            return page
        
        except Exception as err:
            logger.error(f"Ошибка при получении списка сессий: {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при получении списка сессий"
            )


    async def deactivate_session(self, session_id: str, user_id: str, user_role: str) -> None:
        """
        Деактивирует сессию\n
        `session_id` - ID сессии\n
        `user_id` - ID пользователя, выполняющего деактивацию\n
        `user_role` - Роль пользователя, выполняющего деактивацию\n
        В случае ошибки возвращает HTTPException
        """
        try:
            session = await self.get_session_by_id(session_id)
            if not session:
                return

            # Проверка прав доступа
            if str(session.user_id) != user_id and user_role not in self.admin_roles:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="У вас нет прав для деактивации этой сессии")

            await self.session_repository.deactivate_session(session_id)
            await FastAPICache.clear(f"sessions")
            logger.info(f"[deactivate_session] Сессия {session_id} деактивирована пользователем {user_id} с ролью {user_role}")

        except HTTPException:
            raise
        except Exception as err:
            await self.db.rollback()
            logger.error(f"[deactivate_session] Ошибка при деактивации сессии {session_id}: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при деактивации сессии")

    async def terminate_other_sessions(self, current_session_id: str, user_id: str) -> None:
        """
        Завершает все сессии пользователя, кроме текущей\n
        `current_session_id` - ID текущей сессии, которую нужно оставить активной\n
        `user_id` - ID пользователя\n
        В случае ошибки возвращает HTTPException
        """
        try:
            session = await self.get_session_by_id(current_session_id)
            if not session:
                return

            if str(session.user_id) != user_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="У вас нет прав для завершения других сессий")
            
            await self.session_repository.terminate_other_sessions(user_id, current_session_id)
            await FastAPICache.clear(f"sessions")
            logger.info(f"[terminate_other_sessions] Все сессии пользователя {user_id}, кроме текущей, завершены")

        except Exception as err:
            await self.db.rollback()
            logger.error(f"[terminate_other_sessions] Ошибка при завершении других сессий пользователя {user_id}: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при завершении других сессий")

    async def deactivate_all_sessions(self, user_id: str) -> None:
        """
        Деактивирует все сессии пользователя\n
        `user_id` - ID пользователя\n
        В случае ошибки возвращает HTTPException
        """
        try:
            await self.session_repository.deactivate_all_sessions(user_id)
            await FastAPICache.clear(f"sessions")
            logger.info(f"[deactivate_all_sessions] Все сессии пользователя {user_id} деактивированы")

        except Exception as err:
            await self.db.rollback()
            logger.error(f"[deactivate_all_sessions] Ошибка при деактивации всех сессий пользователя {user_id}: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при деактивации всех сессий")
