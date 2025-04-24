# backend/api/auth/schemas.py
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import date, datetime
import uuid
# Импортируем Enum из моделей
from core.models.user import RoleEnum, DopRoleEnum
from core.security.password import password_manager # Для валидации пар

# --- Схемы для запросов ---
# Схема для создания пользователя
class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="Email пользователя (уникальный)")
    username: str = Field(..., min_length=3, max_length=80, description="Имя пользователя (уникальное)")
    password: str = Field(..., min_length=8, description="Пароль")
    name: str = Field(..., max_length=128, description="Полное имя")
    phone: Optional[str] = Field(None, max_length=25, description="Телефон")
    
    @validator('password')
    def validate_password(cls, v):
        """
        Валидация пароля по требованиям безопасности
        """
        is_valid, errors = password_manager.validate_password(v)
        if not is_valid:
            # Объединяем ошибки в одну строку для HTTPException
            raise ValueError(", ".join(errors))
        return v

    @validator('username')
    def validate_username(cls, v):
        """
        Валидация имени пользователя
        """
        if not v.isalnum():
            raise ValueError('Username должен содержать только буквы и цифры')
        return v

# Схема для аутентификации пользователя
class UserLogin(BaseModel):
    """
    Схема для аутентификации пользователя
    """
    username_or_email: str = Field(..., description="Имя пользователя или Email")
    password: str = Field(..., description="Пароль")

# Схема для запроса сброса пароля
class RequestPasswordReset(BaseModel):
    """
    Схема для запроса сброса пароля
    """
    email: EmailStr

# Схема для сброса пароля
class ResetPassword(BaseModel):
    """
    Схема для сброса пароля
    """
    token: str = Field(..., description="Токен из email")
    new_password: str = Field(..., min_length=8, description="Новый пароль")

    @validator('new_password')
    def validate_password(cls, v):
        """
        Валидация нового пароля
        """
        is_valid, errors = password_manager.validate_password(v)
        if not is_valid:
            raise ValueError(", ".join(errors))
        return v

# --- Схемы для ответов ---
# Схема для ответа на запрос сброса пароля
class TokenResponse(BaseModel):
    """
    Схема для ответа на запрос сброса пароля
    """
    access_token: str
    token_type: str = "bearer"

# Схема для базовой информации о пользователе
class UserBase(BaseModel):
    """
    Схема для базовой информации о пользователе
    """
    id: int
    username: str
    email: EmailStr
    name: str
    phone: Optional[str] = None


    role: RoleEnum
    dop_role: Optional[DopRoleEnum] = None
    workPosition: Optional[str] = None
    company: Optional[str] = None
    city: Optional[str] = None
    gender: Optional[str] = None
    uuid: uuid.UUID

    is_active: bool
    is_verified: bool

    class Config:
        from_attributes = True # Для преобразования из модели SQLAlchemy

# Схема для публичной информации о пользователе
class UserPublicProfile(UserBase):
    """
    Схема для публичной информации о пользователе
    """
    # Исключаем чувствительные поля
    pass

# Схема для приватной информации о пользователе
class UserPrivateProfile(UserBase):
    """
    Схема для приватной информации о пользователе
    """
    # Добавляем поля, видимые только владельцу
    user_email: Optional[str] = None
    telegram_id: Optional[str] = None
    dateEmployment: Optional[date] = None
    dateBirthday: Optional[date] = None
    bitrixId: Optional[int] = None
    created_at: datetime
    last_login: Optional[datetime] = None

# Схема для ответа на запрос
class MessageResponse(BaseModel):
    """
    Схема для ответа на запрос
    """
    message: str

# Схема для ответа на запрос CSRF токена
class CSRFTokenResponse(BaseModel):
    """
    Схема для ответа на запрос CSRF токена
    """
    csrf_token: str
