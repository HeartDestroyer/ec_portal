# backend/api/v1/auth/services/registration_service.py - Сервис для регистрации пользователя

# TODO: Запилить возможность выбора пользователя своей группы, если он сотрудник компании, понять как это сделать

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import Optional

from core.services.base_service import BaseService
from core.interfaces.auth.auth_services import RegistrationServiceInterface
from core.interfaces.auth.auth_repositories import UserRepositoryInterface
from core.models.user import User
from backend.core.security.password_service import password_manager
from api.v1.schemas import MessageResponse
from api.v1.auth.schemas.request_schemas import UserCreate
from api.v1.dependencies import EmailManager, JWTHandler
from utils.functions import format_phone_number

class RegistrationService(BaseService, RegistrationServiceInterface):
    """
    Сервис для регистрации пользователя

    Методы:
        - `register_service()` - Регистрация нового пользователя
        - `verify_email_service()` - Подтверждение почты после перехода по ссылке в письме
    """
    def __init__(self, db: AsyncSession, redis: Optional[Redis], user_repository: UserRepositoryInterface, email_manager: EmailManager, jwt_handler: JWTHandler):
        super().__init__(db, redis)
        self.user_repository = user_repository
        self.email_manager = email_manager
        self.jwt_handler = jwt_handler

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
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь с таким логином или почтой уже существует")
            
            formatted_phone = format_phone_number(user_data.phone)
            hashed_password = password_manager.hash_password(user_data.password)

            clean_data = {
                **user_data.model_dump(exclude={"password", "phone"}),
                "phone": formatted_phone,
                "hashed_password": hashed_password,
                "is_active": False,
                "is_verified": False
            }

            new_user = await self.user_repository.create_user(clean_data)

            try:
                await self.email_manager.send_verification_email(new_user.email, str(new_user.id))
            except Exception as err:
                self.log_error(f"Ошибка в отправке письма для подтверждения {new_user.email}: {err}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Ошибка при отправке письма для подтверждения почты, обратитесь к администратору"
                )

            return new_user
            
        except HTTPException:
            raise
        except Exception as err:
            self.log_error(f"Ошибка при регистрации пользователя: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при регистрации пользователя")

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
                self.log_error(f"Ошибка при проверке токена подтверждения почты: {err}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недействительный токен подтверждения почты")
            
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь не найден")
            
            if user.is_verified:
                return MessageResponse(message="Почта уже подтверждена")
                
            user.is_verified = True
            user.is_active = True
            await self.commit_transaction()
            
            self.log_info(f"Почта успешно подтверждена для пользователя {user_id}")
            return MessageResponse(message="Почта успешно подтверждена")
            
        except HTTPException:
            raise
        except Exception as err:
            self.log_error(f"Ошибка при подтверждении email: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при подтверждении email")


