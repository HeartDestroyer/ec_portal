# backend/repositories/password_repository.py - Репозиторий для работы с паролями

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
from typing import Optional

from core.models.user import User
from repositories.base_repository import BaseRepository
from core.extensions.logger import logger

class PasswordRepository(BaseRepository[User]):
    """
    Репозиторий для операций, связанных с паролями и безопасностью для работы с БД

    Методы:
        - `update_password_hash` - Обновляет хеш пароля пользователя
        - `get_password_hash` - Получает хеш пароля пользователя
        - `increment_failed_attempts` - Увеличивает счетчик неудачных попыток входа
        - `set_lockout_time` - Устанавливает время блокировки пользователя
        - `reset_failed_attempts` - Сбрасывает счетчик неудачных попыток и блокировку
        - `get_security_info` - Получает информацию о безопасности пользователя
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def update_password_hash(self, user_id: str, new_password_hash: str) -> bool:
        """
        Обновляет хеш пароля пользователя в БД\n
        `user_id` - ID пользователя\n
        `new_password_hash` - Новый хеш пароля\n
        Возвращает True, если пароль обновлен, иначе False
        """
        try:
            stmt = update(User).where(User.id == user_id).values(hashed_password=new_password_hash)
            result = await self.session.execute(stmt)
            await self.session.commit()
            
            logger.info(f"[update_password_hash] Пароль пользователя {user_id} обновлен")
            return result.rowcount > 0
        except Exception as err:
            await self.session.rollback()
            logger.error(f"[update_password_hash] Ошибка обновления пароля: {err}")
            raise
        
    async def get_password_hash(self, user_id: str) -> Optional[str]:
        """
        Получает хеш пароля пользователя\n
        `user_id` - ID пользователя\n
        Возвращает хеш пароля
        """
        try:
            stmt = select(User.hashed_password).where(User.id == user_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as err:
            logger.error(f"[get_password_hash] Ошибка получения хеша пароля: {err}")
            raise

    async def increment_failed_attempts(self, user_id: str) -> int:
        """
        Увеличивает счетчик неудачных попыток входа\n
        `user_id` - ID пользователя\n
        Возвращает количество неудачных попыток
        """
        try:
            # Получаем текущее значение
            stmt = select(User.failed_login_attempts).where(User.id == user_id)
            result = await self.session.execute(stmt)
            current_attempts = result.scalar_one_or_none() or 0
            
            new_attempts = current_attempts + 1
            
            # Обновляем счетчик
            update_stmt = update(User).where(User.id == user_id).values(
                failed_login_attempts=new_attempts
            )
            await self.session.execute(update_stmt)
            await self.session.commit()
            return new_attempts
        
        except Exception as err:
            await self.session.rollback()
            logger.error(f"[increment_failed_attempts] Ошибка увеличения счетчика попыток: {err}")
            raise

    async def set_lockout_time(self, user_id: str, locked_until: datetime) -> bool:
        """
        Устанавливает время блокировки пользователя в БД\n
        `user_id` - ID пользователя\n
        `locked_until` - Время до которого заблокирован\n
        Возвращает True если успешно
        """
        try:
            stmt = update(User).where(User.id == user_id).values(locked_until=locked_until)
            result = await self.session.execute(stmt)
            await self.session.commit()
            return result.rowcount > 0
            
        except Exception as err:
            await self.session.rollback()
            logger.error(f"[set_lockout_time] Ошибка установки времени блокировки: {err}")
            raise

    async def reset_failed_attempts(self, user_id: str) -> bool:
        """
        Сбрасывает счетчик неудачных попыток и блокировку\n
        `user_id` - ID пользователя\n
        Возвращает True, если сброс выполнен, иначе False
        """
        try:
            stmt = update(User).where(User.id == user_id).values(
                failed_login_attempts=0,
                locked_until=None
            )
            result = await self.session.execute(stmt)
            await self.session.commit()
            return result.rowcount > 0
            
        except Exception as err:
            await self.session.rollback()
            logger.error(f"[reset_failed_attempts] Ошибка сброса счетчика неудачных попыток: {err}")
            raise
    
    async def get_security_info(self, user_id: str) -> Optional[dict]:
        """
        Получает информацию о безопасности пользователя из БД\n
        `user_id` - ID пользователя\n
        Возвращает словарь с информацией о безопасности пользователя
        """
        try:
            stmt = select(
                User.failed_login_attempts,
                User.locked_until,
                User.hashed_password
            ).where(User.id == user_id)
            
            result = await self.session.execute(stmt)
            row = result.one_or_none()
            
            if not row:
                return None
            
            return {
                'failed_attempts': row.failed_login_attempts,
                'locked_until': row.locked_until,
                'password_hash': row.hashed_password
            }
            
        except Exception as err:
            logger.error(f"Ошибка получения информации о безопасности: {err}")
            raise
