# backend/core/interfaces/auth/services.py - Интерфейсы для сервисов авторизации и аутентификации

from typing import Protocol
from fastapi import Request

from api.v1.schemas import MessageResponse, Tokens
from api.v1.auth.schemas import UserCreate, UserLogin, ResetPassword
from core.models.user import User

class AuthenticationServiceInterface(Protocol):
    """
    Интерфейс для сервиса аутентификации

    Методы:
        - `authenticate_user_service()` - Аутентификация пользователя
        - `refresh_tokens_service()` - Обновление токенов
        - `logout_service()` - Выход из системы
    """
    
    async def authenticate_user_service(self, credentials: UserLogin, request: Request) -> Tokens: ...
    async def refresh_tokens_service(self, refresh_token: str) -> Tokens: ...
    async def logout_service(self, user_id: str, session_id: str, refresh_token: str) -> None: ...

class RegistrationServiceInterface(Protocol):
    """
    Интерфейс для сервиса регистрации

    Методы:
        - `register_service()` - Регистрация пользователя
        - `verify_email_service()` - Подтверждение email
    """
    
    async def register_service(self, user_data: UserCreate) -> User: ...
    async def verify_email_service(self, token: str) -> MessageResponse: ...

class PasswordServiceInterface(Protocol):
    """
    Интерфейс для сервиса работы с паролями

    Методы:
        - `request_password_reset_service()` - Запрос на сброс пароля
        - `reset_password_service()` - Сброс пароля
    """
    
    async def request_password_reset_service(self, email: str) -> MessageResponse: ...
    async def reset_password_service(self, data: ResetPassword) -> MessageResponse: ...

class EmailServiceInterface(Protocol):
    """
    Интерфейс для email сервиса

    Методы:
        - `send_verification_email()` - Отправка email для подтверждения email
        - `send_password_reset_email()` - Отправка email для сброса пароля
        - `send_notification_email()` - Отправка email для уведомления
    """
    async def send_verification_email(self, email: str, user_id: str) -> None: ...
    async def send_password_reset_email(self, email: str, user_id: str) -> None: ...
    async def send_notification_email(self, email: str, subject: str, message: str) -> None: ...

class TwoFactorServiceInterface(Protocol):
    """
    Интерфейс для сервиса двухфакторной аутентификации

    Методы:
        - `enable_2fa_service()` - Включение двухфакторной аутентификации
        - `disable_2fa_service()` - Выключение двухфакторной аутентификации
        - `verify_2fa_service()` - Проверка двухфакторной аутентификации
    """

    async def enable_2fa_service(self) -> MessageResponse: ...
    async def disable_2fa_service(self) -> MessageResponse: ...
    async def verify_2fa_service(self, token: str) -> MessageResponse: ...
