from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from redis.asyncio import Redis
from typing import Optional, List, Any
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from fastapi_cache.coder import JsonCoder
import json

from core.security.jwt import JWTHandler
from core.models.user import User
from core.models.session import Session
from core.extensions.logger import logger
from core.config.config import settings
from api.v1.session.schemas import SessionFilter, SessionsPage, SessionResponse, UserAgentInfo
from api.v1.session.utils import SessionUtils


class CustomJsonCoder(JsonCoder):
    """
    JsonCoder, который:
      - При записи в Redis отдаёт plain JSON-строку (str), так что с decode_responses=True всё ровно сохраняется/читается как str
      - При загрузке принимает и bytes, и str и всегда возвращает Python-объект
    """    
    def dump(self, value: any) -> any:
        return json.dumps(value, default=self.default)

    def load(self, value: any) -> any:
        text = value.decode("utf-8") if isinstance(value, (bytes, bytearray)) else value
        return json.loads(text)


class SessionManager:
    """
    Класс для управления сессиями пользователей использует паттерн Singleton и Redis для кэширования\n
    Методы:
        - `get_session_by_id` - Получение сессии по ID\n
        - `get_sessions_user` - Получение всех сессий пользователя\n
        - `get_active_sessions_user` - Получение активных сессий пользователя\n
        - `update_session_last_activity` - Обновление времени последней активности сессии\n
        - `create_session` - Создание новой сессии\n
        - `get_sessions_filtered` - Получение списка сессий с фильтром и кэшированием\n
        - `deactivate_session` - Деактивация сессии\n
        - `terminate_other_sessions` - Завершение всех сессий пользователя, кроме текущей\n
        - `deactivate_all_sessions` - Деактивация всех сессий пользователя
    """

    _instance = None
    _init_lock = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SessionManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db: AsyncSession, jwt_handler: Optional[JWTHandler] = None, redis: Optional[Redis] = None):
        if not self._initialized and not SessionManager._init_lock:
            SessionManager._init_lock = True
            self.db = db
            self.jwt_handler = jwt_handler
            self.redis = redis
            self.admin_roles = settings.ADMIN_ROLES
            self.session_utils = SessionUtils()
            self.max_sessions = settings.MAX_ACTIVE_SESSIONS_PER_USER
            self._initialized = True
            SessionManager._init_lock = False

    @cache(expire=3600, coder=CustomJsonCoder, namespace="sessions:one")
    async def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """
        Получает сессию по ID и кэширует её\n
        `session_id` - ID сессии\n
        Возвращает сессию, иначе возвращает None
        """
        try:
            query = select(Session).where(Session.id == session_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        
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
            query = select(Session).where(Session.user_id == user_id).order_by(Session.last_activity.desc())
            result = await self.db.execute(query)
            sessions = result.scalars().all()
            return list(sessions) if sessions else []
        
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
            query = select(Session).where(
                and_(
                    Session.user_id == user_id,
                    Session.is_active == True
                )
            ).order_by(Session.last_activity.desc())
            
            result = await self.db.execute(query)
            sessions = result.scalars().all()
            return list(sessions) if sessions else []
        
        except Exception as err:
            logger.error(f"Ошибка при получении активных сессий пользователя {user_id}: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при получении активных сессий пользователя")

    async def update_session_last_activity(self, session_id: str) -> None:
        """
        Обновляет время последней активности сессии\n
        `session_id` - ID сессии\n
        В случае ошибки возвращает HTTPException
        """
        try:
            session = await self.get_session_by_id(session_id)
            if not session:
                return

            session.last_activity = datetime.utcnow()
            await self.db.commit()
            
            # Инвалидируем кэш
            await FastAPICache.clear(f"sessions")

        except Exception as err:
            logger.error(f"Ошибка при обновлении времени последней активности сессии {session_id}: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при обновлении времени последней активности сессии")


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
            active_sessions = await self.get_active_sessions_user(str(user.id))
            
            # Если у пользователя слишком много активных сессий, деактивируем самые старые
            if len(active_sessions) >= self.max_sessions:
                logger.warning(
                    f"Превышен лимит активных сессий ({self.max_sessions}) для пользователя {user.name}. Деактивация старых сессий"
                )
                
                # Сортируем сессии по времени последней активности
                active_sessions.sort(key=lambda s: s.last_activity)
                
                # Деактивируем старые сессии
                sessions_to_deactivate = active_sessions[:(len(active_sessions) - self.max_sessions + 1)]
                for session in sessions_to_deactivate:
                    await self.deactivate_session(str(session.id), str(user.id), user.role.value)
                    await self.jwt_handler.revoke_tokens(str(user.id), self.redis, str(session.id))
                
                await self.db.commit()

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

            # Инвалидируем кэш
            await FastAPICache.clear(f"sessions")
            
            logger.info(f"Создана новая сессия {new_session.id} для пользователя {user.id}")
            return new_session
        
        except Exception as err:
            await self.db.rollback()
            logger.error(f"Ошибка при создании сессии для пользователя {str(user.id)}: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при создании сессии")

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
                logger.warning(f"Пользователь {user_id} попытался деактивировать сессию {session_id} пользователя {session.user_id}")
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет прав для деактивации этой сессии")

            session.is_active = False
            session.last_activity = datetime.utcnow()
            await self.db.commit()

            # Инвалидируем кэш
            await FastAPICache.clear(f"sessions")
            
            # Отзываем токены только для конкретной сессии
            await self.jwt_handler.revoke_tokens(str(session.user_id), self.redis, str(session.id))
            
            logger.info(f"Сессия {session_id} деактивирована пользователем {user_id} с ролью {user_role}")

        except HTTPException:
            raise
        except Exception as err:
            await self.db.rollback()
            logger.error(f"Ошибка при деактивации сессии {session_id}: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при деактивации сессии")

    async def terminate_other_sessions(self, current_session_id: str, user_id: str) -> None:
        """
        Завершает все сессии пользователя, кроме текущей\n
        `current_session_id` - ID текущей сессии, которую нужно оставить активной\n
        `user_id` - ID пользователя\n
        В случае ошибки возвращает HTTPException
        """
        try:
            query = select(Session).where(
                and_(
                    Session.user_id == user_id,
                    Session.id != current_session_id,
                    Session.is_active == True
                )
            )
            result = await self.db.execute(query)
            sessions = result.scalars().all()

            if not sessions:
                return

            terminated_count = 0
            for session in sessions:
                session.is_active = False
                session.last_activity = datetime.utcnow()
                terminated_count += 1

            await self.db.commit()
            
            # Инвалидируем кэш
            await FastAPICache.clear(f"sessions")

            # Отзыв токенов в Redis для всех сессий, кроме текущей
            for session in sessions:
                await self.jwt_handler.revoke_tokens(user_id, self.redis, str(session.id))
            
            logger.info(f"Завершено {terminated_count} других сессий пользователя {user_id}")

        except Exception as err:
            await self.db.rollback()
            logger.error(f"Ошибка при завершении других сессий пользователя {user_id}: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при завершении других сессий")

    async def deactivate_all_sessions(self, user_id: str) -> None:
        """
        Деактивирует все сессии пользователя\n
        `user_id` - ID пользователя\n
        В случае ошибки возвращает HTTPException
        """
        try:
            sessions = await self.get_active_sessions_user(user_id)
            if not sessions:
                return

            deactivated_count = 0
            for session in sessions:
                session.is_active = False
                session.last_activity = datetime.utcnow()
                deactivated_count += 1

            await self.db.commit()
            
            # Инвалидируем кэш
            await FastAPICache.clear(f"sessions")
            
            # Отзываем все токены пользователя
            await self.jwt_handler.revoke_tokens(user_id, self.redis)
            
            logger.info(f"Деактивировано {deactivated_count} сессий пользователя {user_id}")

        except Exception as err:
            await self.db.rollback()
            logger.error(f"Ошибка при деактивации всех сессий пользователя {user_id}: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при деактивации всех сессий")
