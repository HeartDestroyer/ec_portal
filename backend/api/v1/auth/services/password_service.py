# backend/api/v1/auth/services/password_service.py - Сервис для работы с паролями

# TODO: Запилить в blacklist refresh токены при сбросе пароля

from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import Optional

from core.services.base_service import BaseService
from core.interfaces.auth.auth_services import PasswordServiceInterface
from core.interfaces.auth.auth_repositories import UserRepositoryInterface
from backend.core.security.password_service import password_manager
from api.v1.schemas import MessageResponse
from api.v1.auth.schemas import ResetPassword
from api.v1.dependencies import EmailManager, JWTHandler, SessionManager

class PasswordService(BaseService, PasswordServiceInterface):
    """
    Сервис для работы с паролями\n
    
    Методы:
        - `request_password_reset_service()` - Запрос на сброс пароля
        - `reset_password_service()` - Сброс пароля
    """

    def __init__(self, db: AsyncSession, redis: Optional[Redis], user_repository: UserRepositoryInterface, email_manager: EmailManager, jwt_handler: JWTHandler, session_manager: SessionManager):
        super().__init__(db, redis)
        self.user_repository = user_repository
        self.email_manager = email_manager
        self.jwt_handler = jwt_handler
        self.session_manager = session_manager

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
