# backend/api/v1/auth/services/password_service.py - Координация между слоями для работы с паролями

# TODO: Запилить в blacklist refresh токены при сбросе пароля

from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import Optional

from core.services.base_service import BaseService
from core.interfaces.auth.auth_services import PasswordServiceInterface
from core.interfaces.auth.auth_repositories import UserRepositoryInterface
from core.security.password_service import password_manager, PasswordValidationResult, BruteForceStatus
from api.v1.schemas import MessageResponse
from api.v1.auth.schemas import ResetPassword
from api.v1.dependencies import EmailManager, JWTHandler, SessionManager
from repositories.password_repository import PasswordRepository

class PasswordService(BaseService, PasswordServiceInterface):
    """
    Сервис для работы с паролями\n
    Реализует бизнес-логику на уровне приложения

    Методы:
        - `validate_and_hash_password` - Валидирует пароль и возвращает его хеш
        - `verify_user_password` - Проверяет пароль пользователя с учетом защиты от брутфорса
        - `change_user_password` - Изменяет пароль пользователя
        - `check_user_lockout_status` - Проверяет статус блокировки пользователя
        - `request_password_reset_service` - Запрос на сброс пароля
        - `reset_password_service` - Сброс пароля
    """

    def __init__(self, db: AsyncSession, redis: Optional[Redis], user_repository: UserRepositoryInterface, email_manager: EmailManager, jwt_handler: JWTHandler, session_manager: SessionManager, password_repository: PasswordRepository):
        super().__init__(db, redis)
        self.user_repository = user_repository
        self.email_manager = email_manager
        self.jwt_handler = jwt_handler
        self.session_manager = session_manager
        self.password_repository = password_repository
        self.password_manager = password_manager

    async def validate_and_hash_password(self, password: str) -> tuple[str, PasswordValidationResult]:
        """
        Валидирует пароль и возвращает его хеш\n
        `password` - Пароль пользователя\n
        Возвращает: (hashed_password, validation_result)
        """
        # Валидация через core
        validation = self.password_manager.validate_password(password)
        
        if not validation.is_valid:
            raise ValueError(f"Пароль не соответствует требованиям: {', '.join(validation.errors)}")
        
        # Хеширование через core
        hashed_password = self.password_manager.hash_password(password)
        
        self.log_info(f"Пароль валидирован и хеширован, сила: {validation.strength.value}")
        return hashed_password, validation
    
    async def verify_user_password(self, user_id: str, password: str) -> tuple[bool, BruteForceStatus]:
        """
        Проверяет пароль пользователя с учетом защиты от брутфорса\n
        `user_id` - ID пользователя\n
        `password` - Пароль пользователя\n
        Возвращает: (password_valid, brute_force_status)
        """
        # Получаем информацию о безопасности из БД
        security_info = await self.password_repository.get_security_info(user_id)
        if not security_info:
            # Выполняем dummy операцию для защиты от timing attacks
            self.password_manager.verify_password("dummy", "dummy_hash")
            raise ValueError("Пользователь не найден")
        
        # Проверяем статус блокировки через core
        lockout_status = self.password_manager.calculate_lockout_status(
            security_info['failed_attempts'],
            security_info['locked_until']
        )
        
        # Если блокировка истекла, сбрасываем в БД
        if security_info['locked_until'] and not lockout_status.is_locked:
            await self.password_repository.reset_failed_attempts(user_id)
            lockout_status = BruteForceStatus(
                is_locked=False,
                attempts_remaining=self.password_manager.max_failed_attempts,
                locked_until=None,
                lockout_duration=None
            )
        
        # Если пользователь заблокирован
        if lockout_status.is_locked:
            logger.warning(f"Попытка входа заблокированного пользователя {user_id}")
            return False, lockout_status
        
        # Проверяем пароль через core
        password_valid = self.password_manager.verify_password(password, security_info['password_hash'])
        
        if password_valid:
            # Пароль верный - сбрасываем попытки в БД
            await self.password_repository.reset_failed_attempts(user_id)
            final_status = BruteForceStatus(
                is_locked=False,
                attempts_remaining=self.password_manager.max_failed_attempts,
                locked_until=None,
                lockout_duration=None
            )
            logger.info(f"Успешная аутентификация пользователя {user_id}")
        else:
            # Пароль неверный - увеличиваем счетчик в БД
            new_attempts = await self.password_repository.increment_failed_attempts(user_id)
            
            # Проверяем, нужно ли блокировать
            if self.password_manager.should_lock_user(new_attempts):
                lockout_time = self.password_manager.calculate_lockout_end_time()
                await self.password_repository.set_lockout_time(user_id, lockout_time)
            
            # Получаем обновленный статус
            updated_security = await self.password_repository.get_security_info(user_id)
            final_status = self.password_manager.calculate_lockout_status(
                updated_security['failed_attempts'],
                updated_security['locked_until']
            )
            
            logger.warning(f"Неудачная попытка входа для пользователя {user_id}, осталось попыток: {final_status.attempts_remaining}")
        
        return password_valid, final_status
    
    async def change_user_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """
        Изменяет пароль пользователя\n
        `user_id` - ID пользователя\n
        `old_password` - Старый пароль\n
        `new_password` - Новый пароль\n
        Возвращает: True - если пароль успешно изменен, False - если нет
        """
        # Проверяем старый пароль
        password_valid, lockout_status = await self.verify_user_password(user_id, old_password)
        
        if lockout_status.is_locked:
            raise ValueError("Аккаунт заблокирован")
            
        if not password_valid:
            raise ValueError("Неверный текущий пароль")
        
        # Валидируем и хешируем новый пароль
        new_password_hash, _ = await self.validate_and_hash_password(new_password)
        
        # Обновляем в БД
        success = await self.password_repository.update_password_hash(user_id, new_password_hash)
        
        if success:
            self.log_info(f"Пароль пользователя {user_id} успешно изменен")
        
        return success
    
    def generate_secure_password(self, length: int = 12) -> str:
        """
        Генерирует безопасный пароль\n
        `length` - Длина пароля\n
        Возвращает безопасный пароль
        """
        return self.password_manager.generate_random_password(length)
    
    async def check_user_lockout_status(self, user_id: str) -> BruteForceStatus:
        """
        Проверяет статус блокировки пользователя\n
        `user_id` - ID пользователя\n
        Возвращает статус блокировки пользователя
        """
        security_info = await self.password_repository.get_security_info(user_id)
        if not security_info:
            raise ValueError("Пользователь не найден")
        
        return self.password_manager.calculate_lockout_status(
            security_info['failed_attempts'],
            security_info['locked_until']
        )

    async def request_password_reset_service(self, email: str) -> MessageResponse:
        """
        Запрос на сброс пароля\n
        `email` - Почта пользователя\n
        Возвращает сообщение об успешной отправке письма
        """
        try:            
            user = await self.user_repository.get_by_login_or_email(email)
            if not user:
                self.log_info(f"Запрос на сброс пароля для несуществующей почты: {email}")
                return MessageResponse(message="Если пользователь существует, письмо для сброса пароля было отправлено")
            
            if not user.is_active:
                self.log_info(f"Запрос на сброс пароля для неактивного пользователя: {email}")
                return MessageResponse(message="Если пользователь существует, письмо для сброса пароля было отправлено")
            
            await self.email_manager.send_password_reset_email(user.email, str(user.id))
            return MessageResponse(message="Если пользователь существует, письмо для сброса пароля было отправлено")
            
        except HTTPException:
            raise
        except Exception as err:
            self.log_error(f"Ошибка при запросе сброса пароля: {err}")
            return MessageResponse(message="Если пользователь существует, письмо для сброса пароля было отправлено")

    async def reset_password_service(self, data: ResetPassword) -> MessageResponse:
        """
        Сброс пароля и добавление старого refresh токена в черный список\n
        `data` - Данные для сброса пароля в виде ResetPassword\n
        Возвращает сообщение об успешном сбросе пароля
        """
        try:
            try:
                payload = self.jwt_handler.decode_reset_token(data.token)
                user_id = payload.get("user_id")
                if not user_id:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недействительный токен сброса пароля")
                
            except Exception as err:
                self.log_error(f"Ошибка при проверке токена сброса пароля: {err}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недействительный токен сброса пароля")
            
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь не найден")
            
            if not user.is_active:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь деактивирован, обратитесь к администратору")
            
            hashed_password = password_manager.hash_password(data.new_password)
            user.hashed_password = hashed_password
            user.last_password_change = datetime.utcnow()
            
            # Сбрасываем неудачные попытки входа и разблокируем аккаунт
            await password_manager.reset_failed_attempts(user)
            
            # Деактивируем все сессии пользователя
            active_sessions = await self.session_service.get_active_sessions_user(str(user.id))
            if active_sessions:
                for session in active_sessions:
                    await self.session_service.deactivate_session(str(session.id), str(user.id), user.role)
            await self.jwt_handler.revoke_tokens(str(user.id), self.redis)
            self.log_info(f"Отозваны все токены пользователя {user_id} при сбросе пароля")
            
            await self.commit_transaction()
            self.log_info(f"Пароль успешно изменен для пользователя {user_id}")
            
            return MessageResponse(message="Пароль успешно изменен")
            
        except HTTPException:
            raise
        except Exception as err:
            self.log_error(f"Ошибка при сбросе пароля: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Ошибка при сбросе пароля")
