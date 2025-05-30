# backend/repositories/password_repository.py - Репозиторий для работы с паролями

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta
from typing import Optional
from core.models.user import User
from repositories.base_repository import BaseRepository
from backend.core.security.password_service import password_manager
from core.extensions.logger import logger

class PasswordRepository(BaseRepository[User]):
    """
    Репозиторий для операций, связанных с паролями и безопасностью

    Методы:
        - `update_password_hash` - Обновляет хеш пароля пользователя
        - `get_password_hash` - Получает хеш пароля пользователя
        - `increment_failed_attempts` - Увеличивает счетчик неудачных попыток входа + 
        - `reset_failed_attempts` - Сбрасывает счетчик неудачных попыток и блокировку
        - `get_security_info` - Получает информацию о безопасности пользователя
        - `check_lockout_status` - Проверяет статус блокировки пользователя + 
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def update_password_hash(self, user_id: str, new_password_hash: str) -> bool:
        """
        Обновляет хеш пароля пользователя\n
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
        """Получает хеш пароля пользователя"""
        try:
            stmt = select(User.password_hash).where(User.id == user_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as err:
            logger.error(f"[get_password_hash] Ошибка получения хеша пароля: {err}")
            raise

    async def increment_failed_attempts(self, user_id: str) -> int:
        """Увеличивает счетчик неудачных попыток входа"""
        try:
            # Получаем текущее значение
            stmt = select(User.failed_login_attempts).where(User.id == user_id)
            result = await self.db.execute(stmt)
            current_attempts = result.scalar_one_or_none() or 0
            
            new_attempts = current_attempts + 1
            
            # Обновляем счетчик
            update_stmt = update(User).where(User.id == user_id).values(
                failed_login_attempts=new_attempts
            )
            await self.db.execute(update_stmt)
            
            # Проверяем, нужно ли блокировать
            if password_manager.should_lock_user(new_attempts):
                lockout_time = password_manager.calculate_lockout_end_time()
                lock_stmt = update(User).where(User.id == user_id).values(
                    locked_until=lockout_time
                )
                await self.db.execute(lock_stmt)
                logger.warning(f"Пользователь {user_id} заблокирован до {lockout_time}")
            
            await self.db.commit()
            return new_attempts
            
        except Exception as err:
            await self.db.rollback()
            logger.error(f"Ошибка увеличения счетчика попыток: {err}")
            raise
    
    async def reset_failed_attempts(self, user_id: str) -> bool:
        """Сбрасывает счетчик неудачных попыток и блокировку"""
        try:
            stmt = update(User).where(User.id == user_id).values(
                failed_login_attempts=0,
                locked_until=None
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            logger.debug(f"Сброшены неудачные попытки для пользователя {user_id}")
            return result.rowcount > 0
            
        except Exception as err:
            await self.db.rollback()
            logger.error(f"Ошибка сброса попыток: {err}")
            raise
    
    async def get_security_info(self, user_id: str) -> Optional[dict]:
        """Получает информацию о безопасности пользователя"""
        try:
            stmt = select(
                User.failed_login_attempts,
                User.locked_until,
                User.password_hash
            ).where(User.id == user_id)
            
            result = await self.db.execute(stmt)
            row = result.one_or_none()
            
            if not row:
                return None
            
            return {
                'failed_attempts': row.failed_login_attempts,
                'locked_until': row.locked_until,
                'password_hash': row.password_hash
            }
            
        except Exception as err:
            logger.error(f"Ошибка получения информации о безопасности: {err}")
            raise
    
    async def check_lockout_status(self, user_id: str) -> BruteForceStatus:
        """Проверяет статус блокировки пользователя"""
        security_info = await self.get_security_info(user_id)
        if not security_info:
            raise ValueError("Пользователь не найден")
        
        # Используем password_manager для вычислений
        status = password_manager.calculate_lockout_status(
            security_info['failed_attempts'],
            security_info['locked_until']
        )
        
        # Если блокировка истекла, сбрасываем счетчики
        if security_info['locked_until'] and not status.is_locked:
            await self.reset_failed_attempts(user_id)
        
        return status
