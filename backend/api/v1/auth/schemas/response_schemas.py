# backend/api/v1/auth/schemas/response_schemas.py - Схемы для ответов на запросы

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import date, datetime
from pydantic.types import UUID4
import uuid

from core.models.user import Gender, Company, City, Role, AdditionalRole

BASE_CONFIG = ConfigDict(
    from_attributes=True,
    json_encoders={
        uuid.UUID: str,
        UUID4: str
    }
)

class UserPublicProfile(BaseModel):
    """
    Схема для публичной информации о пользователе\n
    Для получения публичной информации о пользователе - например при просмотре групп / департаментов\n
        - `email` - Почта пользователя
        - `name` - Имя пользователя
        - `phone` - Номер телефона пользователя
        - `photo_url` - URL фото пользователя
        - `photo_url_small` - URL уменьшенного фото пользователя
        - `work_position` - Должность пользователя
        - `date_employment` - Дата трудоустройства пользователя
        - `telegram_id` - ID пользователя в ТГ
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
        - `id` - ID пользователя
        - `login` - Логин пользователя
        - `email` - Почта пользователя
        - `name` - Имя пользователя
        - `phone` - Номер телефона пользователя
        - `department_id` - ID отдела пользователя
        - `group_id` - ID группы пользователя
        - `work_position` - Должность пользователя
        - `date_employment` - Дата трудоустройства пользователя
        - `city` - Город пользователя
        - `date_birthday` - Дата рождения пользователя
        - `company` - Компания пользователя
        - `qr_code_vcard` - QR код для визитки пользователя
        - `user_email` - Рабочая почта пользователя
        - `telegram_id` - ID пользователя в ТГ
        - `gender` - Пол пользователя
        - `photo_url` - URL фото пользователя
        - `bio` - Доп. информация о пользователе
        - `role` - Роль пользователя
        - `additional_role` - Дополнительная роль пользователя
        - `updated_at` - Дата обновления пользователя
        - `last_login` - Дата последнего входа пользователя
        - `failed_login_attempts` - Количество неудачных попыток входа пользователя
        - `locked_until` - Дата блокировки пользователя
        - `last_password_change` - Дата последнего изменения пароля пользователя
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
    Схема для ответа на запрос CSRF токена
        - `csrf_token` - CSRF токен для защиты от CSRF атак
    """
    model_config = BASE_CONFIG
    
    csrf_token: str = Field(..., description="CSRF токен для защиты от CSRF атак")
