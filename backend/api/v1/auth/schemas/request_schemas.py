# backend/api/v1/auth/schemas/request_schemas.py - Схемы для запросов на аутентификацию и регистрацию

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional
from pydantic.types import UUID4
import uuid

from backend.core.security.password_service import password_manager

BASE_CONFIG = ConfigDict(
    from_attributes=True,
    json_encoders={
        uuid.UUID: str,
        UUID4: str
    }
)

class UserCreate(BaseModel):
    """
    Схема для создания пользователя из формы регистрации
        - `login` - Имя пользователя (уникальное)
        - `email` - Почта пользователя (уникальная)
        - `name` - Полное имя
        - `password` - Пароль
        - `phone` - Номер телефона
    """
    model_config = BASE_CONFIG

    login: str = Field(..., min_length=3, max_length=80, description="Имя пользователя (уникальное)")
    email: EmailStr = Field(..., description="Почта пользователя (уникальная)")
    name: str = Field(..., max_length=128, description="Полное имя")
    password: str = Field(..., description="Пароль")
    phone: Optional[str] = Field(None, max_length=25, description="Номер телефона")
    
    @field_validator('password')
    def validate_password(cls, v: str) -> str:
        is_valid, errors = password_manager.validate_password(v)
        if not is_valid:
            raise ValueError("\n".join(errors))
        return v

    @field_validator('login')
    def validate_login(cls, v: str) -> str:
        if not v.replace('_', '').isalnum():
            raise ValueError('Логин должен содержать только буквы, цифры и подчеркивания')
        
        if v[0].isdigit():
            raise ValueError('Логин не может начинаться с цифры')
        
        reserved_words = {'admin', 'root', 'user', 'api', 'www', 'mail', 'ftp'}
        if v in reserved_words:
            raise ValueError('Этот логин зарезервирован системой')
        return v
    
class UserLogin(BaseModel):
    """
    Схема для аутентификации пользователя из формы входа
        - `login_or_email` - Имя пользователя или почта
        - `password` - Пароль
    """
    model_config = BASE_CONFIG
    
    login_or_email: str = Field(..., description="Имя пользователя или почта")
    password: str = Field(..., description="Пароль")

    @field_validator('login_or_email')
    def validate_login_or_email(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('Логин или почта должена содержать минимум 3 символа')
        return v

class RequestPasswordReset(BaseModel):
    """
    Схема для запроса сброса пароля из формы запроса сброса пароля
        - `email` - Почта пользователя
    """
    model_config = BASE_CONFIG
    
    email: EmailStr = Field(..., description="Почта пользователя")

class ResetPassword(BaseModel):
    """
    Схема для сброса пароля из формы сброса пароля
        - `token` - Токен из письма
        - `new_password` - Новый пароль
    """
    model_config = BASE_CONFIG
    
    token: str = Field(..., description="Токен из письма")
    new_password: str = Field(..., min_length=8, description="Новый пароль")

    @field_validator('new_password')
    def validate_password(cls, v: str) -> str:
        is_valid, errors = password_manager.validate_password(v)
        if not is_valid:
            error_message = "Требования к паролю не выполнены:\n" + "\n".join(errors)
            raise ValueError(error_message)
        return v
