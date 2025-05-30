# backend/core/interfaces/session/session_repositories.py - Интерфейс для репозитория сессий

from typing import List

from core.models.session import Session

class SessionRepositoryInterface:
    """
    Интерфейс для репозитория сессий

    Методы:
        - `update_session_last_activity` - Обновляет время последней активности сессии
        - `get_session_by_id` - Получает сессию по ID
        - `get_sessions_by_user` - Получает все сессии пользователя
        - `get_active_sessions_by_user` - Получает активные сессии пользователя
        - `deactivate_session` - Деактивирует сессию
        - `terminate_other_sessions` - Завершает все сессии пользователя, кроме текущей
        - `deactivate_all_sessions` - Деактивирует все сессии пользователя
    """
    async def update_session_last_activity(self, session_id: str) -> None: ...
    async def get_session_by_id(self, session_id: str) -> Session: ...
    async def get_sessions_by_user(self, user_id: str) -> List[Session]: ...
    async def get_active_sessions_by_user(self, user_id: str) -> List[Session]: ...
    async def deactivate_session(self, session_id: str) -> bool: ...
    async def terminate_other_sessions(self, user_id: str, current_session_id: str) -> int: ...
    async def deactivate_all_sessions(self, user_id: str) -> int: ...
