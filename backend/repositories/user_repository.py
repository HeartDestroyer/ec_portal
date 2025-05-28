# backend/repositories/user_repository.py - Репозиторий для работы с пользователями

from typing import Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.base_repository import BaseRepository
from core.models.user import User

class UserRepository(BaseRepository[User]):
    """
    Репозиторий для работы с пользователями\n
    `session` - Сессия базы данных\n
    `model` - Модель базы данных

    Методы:
        - `get_by_id()` - Находит пользователя по ID
        - `get_by_login_or_email()` - Находит пользователя по login или email
        - `create_user()` - Создает нового пользователя
        - `update_user()` - Обновляет данные пользователя
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Находит пользователя по ID в таблице User\n
        `user_id` - ID пользователя\n
        Возвращает пользователя или None
        """
        query = select(User).where(User.id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_login_or_email(self, login_or_email: str) -> Optional[User]:
        """
        Находит пользователя по login или email в таблице User\n
        `login_or_email` - login/email пользователя\n
        Возвращает пользователя или None
        """
        query = select(User).where(
            or_(User.login == login_or_email, User.email == login_or_email)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_user(self, user_data: dict) -> User:
        """
        Создает нового пользователя\n
        `user_data` - Данные пользователя для регистрации\n
        Возвращает нового пользователя  
        """
        new_user = User(**user_data)
        self.session.add(new_user)
        await self.session.commit()
        return new_user
    
    async def update_user(self, user: User) -> User:
        """
        Обновляет данные пользователя\n
        `user` - Пользователь для обновления\n
        Возвращает обновленного пользователя
        """
        await self.session.commit()
        await self.session.refresh(user)
        return user

    