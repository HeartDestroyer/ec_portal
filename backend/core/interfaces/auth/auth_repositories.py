# backend/core/interfaces/auth/repositories.py - Интерфейсы для репозиториев авторизации и аутентификации

from typing import Protocol, Optional

from api.v1.auth.schemas import UserCreate
from core.models.user import User

class UserRepositoryInterface(Protocol):
    """
    Интерфейс для репозитория пользователей

    Методы:
        - `get_by_id` - Находит пользователя по ID
        - `get_by_login_or_email` - Находит пользователя по login или email
        - `create_user` - Создает нового пользователя
        - `update_user` - Обновляет данные пользователя
    """
    async def get_by_id(self, user_id: str) -> Optional[User]: ...
    async def get_by_login_or_email(self, login_or_email: str) -> Optional[User]: ...
    async def create_user(self, user_data: UserCreate) -> User: ...
    async def update_user(self, user: User) -> User: ...
