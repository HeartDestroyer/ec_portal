# backend/api/auth/schemas.py
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import date, datetime
import uuid
# Импортируем Enum из моделей
from core.models.user import Role, AdditionalRole, Gender, Company, City
from core.security.password import password_manager

# Схема для создания пользователя
class UserCreate(BaseModel):
    login: str = Field(..., min_length=3, max_length=80, description="Имя пользователя (уникальное)")
    email: EmailStr = Field(..., description="Email пользователя (уникальный)")
    name: str = Field(..., max_length=128, description="Полное имя")
    password: str = Field(..., description="Пароль")
    phone: Optional[str] = Field(None, max_length=25, description="Телефон")
    
    @field_validator('password')
    def validate_password(cls, v):
        """
        Валидация пароля по требованиям безопасности
        """
        is_valid, errors = password_manager.validate_password(v)
        if not is_valid:
            for error in errors:
                raise ValueError(error)
        return v

    @field_validator('login')
    def validate_login(cls, v):
        """
        Валидация имени пользователя
        """
        if not v.isalnum():
            raise ValueError('Логин должен содержать только буквы и цифры')
        return v

# Схема для аутентификации пользователя
class UserLogin(BaseModel):
    """
    Схема для аутентификации пользователя
    """
    login_or_email: str = Field(..., description="Имя пользователя или Email")
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

    @field_validator('new_password')
    def validate_password(cls, v):
        """
        Валидация нового пароля
        """
        is_valid, errors = password_manager.validate_password(v)
        if not is_valid:
            # Изменяем формат вывода ошибки
            error_message = "Требования к паролю не выполнены: " + "; ".join(errors)
            raise ValueError(error_message)
        return v


# --- Схемы для ответов ---
# Схема для базовой информации о пользователе
class UserBase(BaseModel):
    """
    Схема для базовой информации о пользователе
    """
    id: uuid.UUID
    login: str
    email: EmailStr
    name: str
    role: Role
    phone: Optional[str] = None

    is_active: bool
    is_verified: bool

    class Config:
        from_attributes = True

# Схема для публичной информации о пользователе
class UserPublicProfile(BaseModel):
    """
    Схема для публичной информации о пользователе
    """
    login: str
    email: EmailStr
    name: str
    phone: Optional[str] = None

# Схема для приватной информации о пользователе
class UserPrivateProfile(UserBase):
    """
    Схема для приватной информации о пользователе
    """
    group_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    work_position: Optional[str] = None
    date_employment: Optional[date] = None
    city: Optional[City] = None
    date_birthday: Optional[date] = None
    company: Optional[Company] = None
    bitrix_id: Optional[int] = None
    qr_code_vcard: Optional[str] = None
    user_email: Optional[str] = None
    telegram_id: Optional[str] = None
    gender: Optional[Gender] = None
    photo_url: Optional[str] = None
    photo_url_small: Optional[str] = None
    bio: Optional[str] = None
    role: Role
    additional_role: Optional[AdditionalRole] = None
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    last_password_change: Optional[datetime] = None


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
