# backend/repositories/session_repository.py - Репозиторий для работы с сессиями в БД

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from typing import List
from datetime import datetime

from core.models.session import Session
from repositories.base_repository import BaseRepository

class SessionRepository(BaseRepository[Session]):
    """
    Репозиторий для работы с сессиями в БД

    Методы:
        - `update_session_last_activity` - Обновляет время последней активности сессии
        - `get_session_by_id` - Получает сессию по ID
        - `get_sessions_by_user` - Получает все сессии пользователя
        - `get_active_sessions_by_user` - Получает активные сессии пользователя
        - `deactivate_session` - Деактивирует сессию
        - `terminate_other_sessions` - Завершает все сессии пользователя, кроме текущей
        - `deactivate_all_sessions` - Деактивирует все сессии пользователя
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Session)
    
    async def update_session_last_activity(self, session_id: str) -> None:
        """
        Обновляет время последней активности сессии\n
        `session_id` - ID сессии\n
        """
        stmt = update(Session).where(Session.id == session_id).values(last_activity=datetime.utcnow())
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_session_by_id(self, session_id: str) -> Session:
        """
        Получает сессию по ID\n
        `session_id` - ID сессии\n
        Возвращает сессию, если она существует, иначе None
        """ 
        stmt = select(Session).where(Session.id == session_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_sessions_by_user(self, user_id: str) -> List[Session]:
        """
        Получает все сессии пользователя\n
        `user_id` - ID пользователя\n
        Возвращает список всех сессий пользователя
        """
        stmt = select(Session).where(Session.user_id == user_id)    
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_sessions_by_user(self, user_id: str) -> List[Session]:
        """
        Получает активные сессии пользователя\n
        `user_id` - ID пользователя\n
        Возвращает список активных сессий пользователя, отсортированных по времени последней активности
        """
        stmt = select(Session).where(
            and_(
                Session.user_id == user_id,
                Session.is_active == True
            )
        ).order_by(Session.last_activity.desc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def deactivate_session(self, session_id: str) -> bool:
        """
        Деактивирует сессию\n
        `session_id` - ID сессии\n
        Возвращает True, если сессия была деактивирована, иначе False
        """
        stmt = update(Session).where(Session.id == session_id).values(is_active=False, last_activity=datetime.utcnow())
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def terminate_other_sessions(self, user_id: str, current_session_id: str) -> int:
        """
        Завершает все сессии пользователя, кроме текущей\n
        `user_id` - ID пользователя\n
        `current_session_id` - ID текущей сессии\n
        Возвращает количество завершенных сессий
        """
        stmt = update(Session).where(
            and_(
                Session.user_id == user_id,
                Session.id != current_session_id,
                Session.is_active == True
            )
        ).values(is_active=False, last_activity=datetime.utcnow())
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def deactivate_all_sessions(self, user_id: str) -> int:
        """
        Деактивирует все сессии пользователя\n
        `user_id` - ID пользователя\n
        Возвращает количество завершенных сессий
        """
        stmt = update(Session).where(
            and_(
                Session.user_id == user_id,
                Session.is_active == True
            )
        ).values(is_active=False, last_activity=datetime.utcnow())
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
