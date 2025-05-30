# backend/api/v1/auth/services/authentication_service.py - Сервис для аутентификации пользователя

from datetime import datetime
from fastapi import HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import Optional

from core.services.base_service import BaseService
from core.interfaces.auth.auth_services import AuthenticationServiceInterface
from core.interfaces.auth.auth_repositories import UserRepositoryInterface
from api.v1.schemas import TokenPayload, Tokens
from api.v1.auth.schemas import UserLogin
from api.v1.dependencies import JWTHandler, SessionManager, EmailManager, settings
from api.v1.session.utils import SessionUtils
from backend.core.security.password_service import password_manager
from core.models.user import User

class AuthenticationService(BaseService, AuthenticationServiceInterface):
    """
    Сервис для аутентификации пользователя

    Методы:
        - `update_user_login_info()` - Обновление информации о последнем входе пользователя
        - `authenticate_user_service()` - Аутентификация пользователя
        - `refresh_tokens_service()` - Обновление токенов
        - `logout_service()` - Выход из системы
    """

    def __init__(self, db: AsyncSession, redis: Optional[Redis], user_repository: UserRepositoryInterface, jwt_handler: JWTHandler, session_manager: SessionManager, email_manager: EmailManager):
        super().__init__(db, redis)
        self.user_repository = user_repository
        self.jwt_handler = jwt_handler
        self.session_manager = session_manager
        self.email_manager = email_manager
        self.session_utils = SessionUtils()
        self.max_sessions = settings.MAX_ACTIVE_SESSIONS_PER_USER
        self.project_name = settings.PROJECT_NAME
        self.developer_tg = settings.DEVELOPER_TG

    async def update_user_login_info(self, user: User) -> None:
        """
        Обновляет информацию о последнем входе пользователя и сбрасывает количество неудачных попыток входа\n
        `user` - Пользователь для обновления\n
        Возвращает обновленного пользователя
        """
        try:
            await password_manager.reset_failed_attempts(user)
            user.last_login = datetime.utcnow()
            await self.user_repository.update_user(user)
        
        except Exception as err:
            self.log_error(f"Ошибка при обновлении информации о входе пользователя {str(user.id)}: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при обновлении информации о входе")

    async def authenticate_user_service(self, credentials: UserLogin, request: Request) -> Tokens:
        """
        Аутентификация пользователя\n
        `credentials` - Учетные данные пользователя в виде UserLogin\n
        Возвращает токены в виде Tokens
        """
        try:
            user = await self.user_repository.get_by_login_or_email(credentials.login_or_email)
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Неверное имя пользователя/почта или пароль")
            
            # Проверка блокировки
            if await password_manager.check_brute_force(user):
                locked_duration = (user.locked_until - datetime.utcnow()).total_seconds()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Аккаунт временно заблокирован. Попробуйте через {int(locked_duration // 60)} минут"
                )

            # Проверяем активность пользователя
            if not user.is_active:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Аккаунт деактивирован, обратитесь к администратору")
            
            # Проверка подтверждения акаунта
            if not user.is_verified:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Аккаунт не подтвержден, обратитесь к администратору")
            
            # Проверка пароля
            if not password_manager.verify_password(credentials.password, user.hashed_password):
                await password_manager.handle_failed_login(user)
                await self.commit_transaction()
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверное имя пользователя/почта или пароль")

            # Сброс счетчика неудачных попыток и обновление last_login
            await self.update_user_login_info(user)

            # Получаем информацию о пользовательском агенте и создаем новую сессию
            # Деактивируем старые сессии если их количество превышает лимит активных сессий
            user_agent_info = await self.session_utils.user_agent_info(request)
            new_session = await self.session_service.create_session(user, user_agent_info)

            message_notification = (
                "<b>Вы успешно вошли в систему</b><br><br>"
                "Данные входа:<br>"
                f"IP-адрес: {user_agent_info.ip_address}<br>"
                f"Местоположение: {user_agent_info.location}<br>"
                f"Устройство: {user_agent_info.browser} • {user_agent_info.os}<br>"
                f"Время входа: {datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S')} (UTC)<br><br>"
                f"<span style='color:red;'>Если это были не вы, сразу же обратитесь в <a href='{self.developer_tg}'>ТГ-чат</a></span>"
            )

            # Отправляем уведомление на почту
            await self.email_manager.send_notification_email(user.email, f"Новый вход в {self.project_name}", message_notification)

            tokens = await self.jwt_handler.create_tokens(
                TokenPayload(
                    user_id=str(user.id),
                    session_id=str(new_session.id),
                    role=user.role
                ),
                self.redis
            )
            return tokens
            
        except HTTPException:
            raise
        except Exception as err:
            self.log_error(f"Ошибка при аутентификации пользователя: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при аутентификации пользователя")

    async def refresh_tokens_service(self, refresh_token: str) -> Tokens:
        """
        Обновление токенов и обновление времени последней активности сессии и добавление старого refresh токена в черный список\n
        `refresh_token` - Токен обновления\n
        Возвращает новые токены в виде Tokens
        """
        payload: Optional[TokenPayload] = None
        try:            
            payload = await self.jwt_handler.verify_token(refresh_token, "refresh", self.redis)
            await self.jwt_handler.set_refresh_token_to_blacklist(refresh_token, self.redis)
            await self.jwt_handler.revoke_tokens(payload.user_id, self.redis, payload.session_id)
            await self.session_service.update_session_last_activity(payload.session_id)
            tokens = await self.jwt_handler.create_tokens(payload, self.redis)
            return tokens
            
        except HTTPException:
            # Деактивируем по реальному payload, если он есть
            if payload:
                await self.session_service.deactivate_session(payload.session_id, payload.user_id, payload.role)
            else:
                # Пытаемся «мягко» достать данные из токена без верификации
                payload = await self.jwt_handler.decode_token(refresh_token)
                if payload:
                    await self.session_service.deactivate_session(payload.session_id, payload.user_id, payload.role)
            await self.jwt_handler.set_refresh_token_to_blacklist(refresh_token, self.redis)
            raise
        except Exception as err:
            self.log_error(f"Ошибка при обновлении токенов: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при обновлении токенов")

    async def logout_service(self, user_id: str, session_id: str, refresh_token: str) -> None:
        """
        Выход из системы и добавление старого refresh токена в черный список\n
        `user_id` - ID пользователя\n
        `session_id` - ID сессии\n
        `refresh_token` - Токен обновления\n
        Возвращает True при успешном выходе
        """
        try:            
            await self.jwt_handler.revoke_tokens(user_id, self.redis, session_id)
            user = await self.user_repository.get_by_id(user_id)
            await self.session_service.deactivate_session(session_id, user_id, user.role)
            await self.jwt_handler.set_refresh_token_to_blacklist(refresh_token, self.redis)
            await self.commit_transaction()
            return True
        except HTTPException:
            raise
        except Exception as err:
            self.log_error(f"Ошибка при выходе из системы: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при выходе из системы")
