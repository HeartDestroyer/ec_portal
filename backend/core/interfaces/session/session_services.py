# backend/core/interfaces/session/session_services.py - Интерфейс для сервиса сессий

from typing import Protocol, List, Dict

from core.models.session import Session
from core.models.user import User

class SessionServiceInterface(Protocol):
    """
    Интерфейс для сервиса сессий

    Методы:
        - `get_session_by_id` - Получает сессию по ID
        - `get_sessions_user` - Получает все сессии пользователя
        - `get_active_sessions_user` - Получает активные сессии пользователя
        - `create_user_session` - Создает новую сессию для пользователя
        - `update_session_activity` - Обновляет активность сессии
        - `terminate_other_sessions` - Завершает все сессии пользователя, кроме текущей
        - `deactivate_all_sessions` - Деактивирует все сессии пользователя
    """
    async def get_session_by_id(self, session_id: str) -> Session: ...
    async def get_sessions_user(self, user_id: str) -> List[Session]: ...
    async def get_active_sessions_user(self, user_id: str) -> List[Session]: ...
    async def create_user_session(self, user: User, device_info: Dict[str, str]) -> Session: ...
    async def update_session_activity(self, session_id: str) -> None: ...
    async def terminate_other_sessions(self, current_session_id: str, user_id: str) -> int: ...
    async def deactivate_all_sessions(self, user_id: str) -> int: ...
