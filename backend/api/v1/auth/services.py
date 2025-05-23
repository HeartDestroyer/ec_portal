from datetime import datetime, timedelta
from fastapi import HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from redis.asyncio import Redis
from typing import Optional
from datetime import datetime
import pyotp

from api.v1.schemas import MessageResponse, TokenPayload, Tokens
from api.v1.dependencies import (
    JWTHandler, EmailManager, SessionManager,
    settings, logger
)
from core.security.password import password_manager
from core.models.user import User
from .schemas import UserCreate, ResetPassword, UserLogin
from api.v1.session.utils import SessionUtils
from utils.functions import format_phone_number


class UserRepository:
    """
    Репозиторий для работы с пользователями\n
    Реализует паттерн Repository, абстрагирующий доступ к данным пользователей

    Методы:
    - `get_by_id()` - Находит пользователя по ID
    - `get_by_login_or_email()` - Находит пользователя по login или email
    - `create_user()` - Создает нового пользователя
    - `update_user()` - Обновляет данные пользователя
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Находит пользователя по ID в таблице User\n
        `user_id` - ID пользователя\n
        Возвращает пользователя или None
        """
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
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
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_user(self, user_data: UserCreate) -> User:
        """
        Создает нового пользователя\n
        `user_data` - Данные пользователя для регистрации\n
        Возвращает нового пользователя  
        """

        formatted_phone = format_phone_number(user_data.phone)
        hashed_password = password_manager.hash_password(user_data.password)

        new_user = User(
            **user_data.model_dump(exclude={"password", 'phone'}),
            phone=formatted_phone,
            hashed_password=hashed_password,
            is_active=False,
            is_verified=False
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        return new_user
    
    async def update_user(self, user: User) -> User:
        """
        Обновляет данные пользователя\n
        `user` - Пользователь для обновления\n
        Возвращает обновленного пользователя
        """
        await self.db.commit()
        await self.db.refresh(user)
        return user


class AuthenticationService:
    """
    Сервис для аутентификации пользователя\n
    Использует паттерн Service, абстрагирующий доступ к данным и бизнес-логику\n
    Методы:
        - `update_user_login_info()` - Обновляет информацию о последнем входе пользователя и сбрасывает количество неудачных попыток входа\n
        - `register_service()` - Регистрация нового пользователя в таблице User\n
        - `authenticate_user_service()` - Аутентификация пользователя (включает в себя проверку блокировки, активность, подтверждение акаунта, пароль и отправку уведомления на почту)\n
        - `refresh_tokens_service()` - Обновление токенов\n
        - `logout_service()` - Выход из системы\n
        - `request_password_reset_service()` - Запрос на сброс пароля\n
        - `reset_password_service()` - Сброс пароля\n
        - `verify_email_service()` - Подтверждение почты\n
        - `enable_2fa_service()` - Двухфакторная аутентификация
        
    TODO:
        - Создать сервис для двухфакторной аутентификации
        - Добавлять в blacklist refresh токены при массовых инвалидациях токенов
    """

    def __init__(self, db: AsyncSession, redis: Optional[Redis], jwt_handler: Optional[JWTHandler], email_manager: Optional[EmailManager]):
        self.db = db
        self.redis = redis
        self.jwt_handler = jwt_handler
        self.email_manager = email_manager
        self.max_sessions = settings.MAX_ACTIVE_SESSIONS_PER_USER
        self.session_service = SessionManager(db, jwt_handler, redis)
        self.session_utils = SessionUtils()
        self.user_repository = UserRepository(db)
        self.tg_chat_url = "https://t.me/XopXeyLalalei"
        self.project_name = settings.PROJECT_NAME

    async def update_user_login_info(self, user: User) -> User:
        """
        Обновляет информацию о последнем входе пользователя и сбрасывает количество неудачных попыток входа\n
        `user` - Пользователь для обновления\n
        Возвращает обновленного пользователя
        """
        try:
            await password_manager.reset_failed_attempts(user)
            user.last_login = datetime.utcnow()
            return await self.user_repository.update_user(user)
        except Exception as err:
            logger.error(f"Ошибка при обновлении информации о входе пользователя {str(user.id)}: {err}")
            raise HTTPException(detail="Ошибка при обновлении информации о входе", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def register_service(self, user_data: UserCreate) -> User:
        """
        Регистрация нового пользователя в таблице User\n
        `user_data` - Данные пользователя для регистрации в виде UserCreate\n
        Возвращает нового пользователя
        """
        try:
            user_login = await self.user_repository.get_by_login_or_email(user_data.login)
            user_email = await self.user_repository.get_by_login_or_email(user_data.email)
            if user_login or user_email:
                raise HTTPException(detail="Пользователь с таким логином или почтой уже существует", status_code=status.HTTP_400_BAD_REQUEST)
            
            new_user = await self.user_repository.create_user(user_data)

            try:
                await self.email_manager.send_verification_email(new_user.email, str(new_user.id))
            except Exception as err:
                logger.error(f"Ошибка в отправке письма для подтверждения {new_user.email}: {err}")
                raise HTTPException(
                    detail="Ошибка при отправке письма для подтверждения почты, обратитесь к администратору", 
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return new_user
            
        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"Ошибка при регистрации пользователя: {err}")
            raise HTTPException(detail="Ошибка при регистрации пользователя", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def authenticate_user_service(self, credentials: UserLogin, request: Request) -> Tokens:
        """
        Аутентификация пользователя\n
        `credentials` - Учетные данные пользователя в виде UserLogin\n
        `request` - Объект запроса FastAPI\n
        Возвращает токены в виде Tokens
        """
        try:
            user = await self.user_repository.get_by_login_or_email(credentials.login_or_email)
            if not user:
                raise HTTPException(detail="Неверное имя пользователя/почта или пароль", status_code=status.HTTP_404_NOT_FOUND)
            
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
                await self.db.commit()
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
                f"<span style='color:red;'>Если это были не вы, сразу же обратитесь в <a href='{self.tg_chat_url}'>ТГ-чат</a></span>"
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
            logger.error(f"Ошибка при аутентификации пользователя: {err}")
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
            logger.error(f"Ошибка при обновлении токенов: {err}")
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
            await self.db.commit()
                        
        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"Ошибка при выходе из системы: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при выходе из системы")

    async def request_password_reset_service(self, email: str) -> MessageResponse:
        """
        Запрос на сброс пароля\n
        `email` - Почта пользователя\n
        Возвращает сообщение об успешной отправке письма
        """
        try:            
            user = await self.user_repository.get_by_login_or_email(email)
            if not user:
                logger.info(f"Запрос на сброс пароля для несуществующей почты: {email}")
                return MessageResponse(message="Если пользователь существует, письмо для сброса пароля было отправлено")
            
            if not user.is_active:
                logger.info(f"Запрос на сброс пароля для неактивного пользователя: {email}")
                return MessageResponse(message="Если пользователь существует, письмо для сброса пароля было отправлено")
            
            await self.email_manager.send_password_reset_email(user.email, str(user.id))
            return MessageResponse(message="Если пользователь существует, письмо для сброса пароля было отправлено")
            
        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"Ошибка при запросе сброса пароля: {err}")
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
                logger.error(f"Ошибка при проверке токена сброса пароля: {err}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Недействительный токен сброса пароля"
                )
            
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
            logger.info(f"Отозваны все токены пользователя {user_id} при сбросе пароля")
            
            await self.db.commit()
            logger.info(f"Пароль успешно изменен для пользователя {user_id}")
            
            return MessageResponse(message="Пароль успешно изменен")
            
        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"Ошибка при сбросе пароля: {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при сбросе пароля"
            )

    async def verify_email_service(self, token: str) -> MessageResponse:
        """
        Подтверждение почты после перехода по ссылке в письме\n
        `token` - Токен подтверждения\n
        Возвращает сообщение об успешном подтверждении
        """
        try:
            try:
                payload = self.jwt_handler.decode_verification_token(token)
                user_id = payload.get("user_id")
                if not user_id:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недействительный токен подтверждения")
                
            except Exception as err:
                logger.error(f"Ошибка при проверке токена подтверждения почты: {err}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Недействительный токен подтверждения почты"
                )
            
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь не найден")
            
            if user.is_verified:
                return MessageResponse(message="Почта уже подтверждена")
                
            user.is_verified = True
            user.is_active = True
            await self.db.commit()
            
            logger.info(f"Почта успешно подтверждена для пользователя {user_id}")
            return MessageResponse(message="Почта успешно подтверждена")
            
        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"Ошибка при подтверждении email: {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при подтверждении email"
            )

    async def enable_2fa_service(self) -> MessageResponse:
        """
        Включение двухфакторной аутентификации\n
        Возвращает сообщение об успешном включении двухфакторной аутентификации
        """
        return MessageResponse(message="TODO: Запилить двухфакторную аутентификацию")
