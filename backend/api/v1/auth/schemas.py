from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional
from datetime import date, datetime
from pydantic.types import UUID4
import uuid
from core.models.user import Gender, Company, City, Role, AdditionalRole
from core.security.password import password_manager

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
        if not v.isalnum():
            raise ValueError('Логин должен содержать только буквы и цифры')
        return v

class UserLogin(BaseModel):
    """
    Схема для аутентификации пользователя из формы входа
    """
    model_config = BASE_CONFIG
    
    login_or_email: str = Field(..., description="Имя пользователя или почта")
    password: str = Field(..., description="Пароль")

class RequestPasswordReset(BaseModel):
    """
    Схема для запроса сброса пароля из формы запроса сброса пароля
    """
    model_config = BASE_CONFIG
    
    email: EmailStr = Field(..., description="Почта пользователя")

class ResetPassword(BaseModel):
    """
    Схема для сброса пароля из формы сброса пароля
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

class UserPublicProfile(BaseModel):
    """
    Схема для публичной информации о пользователе\n
    Для получения публичной информации о пользователе - например при просмотре групп / департаментов
    """
    model_config = BASE_CONFIG
    
    email: EmailStr = Field(..., description="Почта пользователя")
    name: str = Field(..., description="Имя пользователя")
    phone: Optional[str] = Field(None, description="Номер телефона пользователя")
    photo_url: Optional[str] = Field(None, description="URL фото пользователя")
    photo_url_small: Optional[str] = Field(None, description="URL уменьшенного фото пользователя")
    work_position: Optional[str] = Field(None, description="Должность пользователя")
    date_employment: Optional[date] = Field(None, description="Дата трудоустройства пользователя")
    telegram_id: Optional[str] = Field(None, description="ID пользователя в ТГ")

class UserPrivateProfile(BaseModel):
    """
    Схема для приватной информации о пользователе\n
    Для получения приватной информации о пользователе - например при просмотре своего профиля
    """
    model_config = BASE_CONFIG
    
    id: UUID4 = Field(..., description="ID пользователя")
    login: str = Field(..., description="Логин пользователя")
    email: EmailStr = Field(..., description="Почта пользователя")
    name: str = Field(..., description="Имя пользователя")
    phone: Optional[str] = Field(None, description="Номер телефона пользователя")
    department_id: Optional[UUID4] = Field(None, description="ID отдела пользователя")
    group_id: Optional[UUID4] = Field(None, description="ID группы пользователя")
    work_position: Optional[str] = Field(None, description="Должность пользователя")
    date_employment: Optional[date] = Field(None, description="Дата трудоустройства пользователя")
    city: Optional[City] = Field(None, description="Город пользователя")
    date_birthday: Optional[date] = Field(None, description="Дата рождения пользователя")
    company: Optional[Company] = Field(None, description="Компания пользователя")
    qr_code_vcard: Optional[str] = Field(None, description="QR код для визитки пользователя")
    user_email: Optional[str] = Field(None, description="Рабочая почта пользователя")
    telegram_id: Optional[str] = Field(None, description="ID пользователя в ТГ")
    gender: Optional[Gender] = Field(None, description="Пол пользователя")
    photo_url: Optional[str] = Field(None, description="URL фото пользователя")
    bio: Optional[str] = Field(None, description="Доп. информация о пользователе")
    role: Role = Field(..., description="Роль пользователя")
    additional_role: Optional[AdditionalRole] = Field(None, description="Дополнительная роль пользователя")
    updated_at: datetime = Field(..., description="Дата обновления пользователя")
    last_login: Optional[datetime] = Field(None, description="Дата последнего входа пользователя")
    failed_login_attempts: int = Field(0, description="Количество неудачных попыток входа пользователя")
    locked_until: Optional[datetime] = Field(None, description="Дата блокировки пользователя")
    last_password_change: Optional[datetime] = Field(None, description="Дата последнего изменения пароля пользователя")

class CSRFTokenResponse(BaseModel):
    """
    Схема для ответа на запрос CSRF токена\n
    Для получения CSRF токена
    """
    model_config = BASE_CONFIG
    
    csrf_token: str = Field(..., description="CSRF токен для защиты от CSRF атак")
