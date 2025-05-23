from datetime import datetime, date
from typing import Optional, List, Union, Any
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from fastapi import HTTPException, status

from core.models.user import Role, AdditionalRole, Gender, Company, City
from utils.functions import format_phone_number
from api.v1.dependencies import settings

# Фильтры запроса на получение списка пользователей
class UserFilter(BaseModel):
    """
    Фильтры для запроса списка пользователей
    """
    name: Optional[str] = None
    department: Optional[str] = None
    group: Optional[str] = None
    city: Optional[City] = None
    company: Optional[Company] = None
    bitrix_id: Optional[int] = None
    crm_id: Optional[str] = None
    gender: Optional[Gender] = None
    role: Optional[Role] = None
    is_active: Optional[bool] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=100)

# Схема информации о пользователе для пользователя
class UserPublicProfile(BaseModel):
    """
    Схема информации о пользователе для пользователя
    """
    id: str
    old_id: Optional[int] = None
    email: str
    name: str
    phone: Optional[str] = None
    work_position: Optional[str] = None
    date_employment: Optional[datetime] = None
    telegram_id: Optional[str] = None
    photo: Optional[str] = None
    photo_small: Optional[str] = None
    bio: Optional[str] = None

# Схема приватного профиля пользователя для администраторов
class UserPrivateProfile(BaseModel):
    """
    Приватный профиль пользователя для администраторов
    """
    id: str
    old_id: Optional[int] = None
    crm_id: Optional[str] = None
    login: str
    name: str
    email: str
    phone: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{10,14}$')
    is_active: bool
    department: Optional[str] = None
    group: Optional[str] = None
    position: Optional[str] = None
    date_employment: Optional[datetime] = None
    city: Optional[str] = None
    date_birth: Optional[datetime] = None
    company: Optional[str] = None
    bitrix_id: Optional[int] = None
    telegram_id: Optional[str] = None
    gender: Optional[str] = None
    photo: Optional[str] = None
    photo_small: Optional[str] = None
    bio: Optional[str] = None
    role: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# Ответ с данными пользователя
class UserProfileResponse(BaseModel):
    """
    Ответ с данными пользователя
    """
    user: Union[UserPublicProfile, UserPrivateProfile]

# Ответ на запрос на получение списка пользователей для администратора
class UserProfilesResponse(BaseModel):
    """
    Ответ со списком пользователей
    """
    users: List[Union[UserPublicProfile, UserPrivateProfile]]
    total_users: int

# Обновление данных пользователя - комбинированный
class UserUpdateCombined(BaseModel):
    """
    Схема обновления данных пользователя
    """
    # Базовые поля
    login: Optional[str] = Field(None, min_length=3, max_length=32, pattern=r'^[a-zA-Z0-9]+$')
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, min_length=2, max_length=128)
    phone: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{10,14}$')
    date_birth: Optional[date] = None
    photo: Optional[str] = None
    photo_small: Optional[str] = None
    bio: Optional[str] = None

    # Поля для сотрудников
    department_id: Optional[str] = None
    group_id: Optional[str] = None
    position: Optional[str] = None
    user_email: Optional[EmailStr] = None

    # Поля для администраторов
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    date_employment: Optional[date] = None
    city: Optional[City] = None
    company: Optional[Company] = None
    bitrix_id: Optional[int] = Field(None, gt=0)
    telegram_id: Optional[str] = None
    gender: Optional[Gender] = None
    role: Optional[Role] = None
    additional_role: Optional[AdditionalRole] = None

    @field_validator('date_birth')
    def validate_date_birth(cls, v: Optional[date]) -> Optional[date]:
        """
        Валидация даты рождения
        """
        if v is not None:
            today = date.today()
            if v > today:
                raise ValueError('Дата рождения не может быть в будущем')
            if v < date(1900, 1, 1):
                raise ValueError('Дата рождения не может быть раньше 1900 года')
        return v

    @field_validator('date_employment')
    def validate_date_employment(cls, v: Optional[date]) -> Optional[date]:
        """
        Валидация даты трудоустройства
        """
        if v is not None:
            today = date.today()
            if v > today:
                raise ValueError('Дата трудоустройства не может быть в будущем')
        return v

    @model_validator(mode='before')
    @classmethod
    def restrict_admin_fields(cls, data: Any, info: Any) -> Any:
        """
        Проверяет права доступа к полям при обновлении
        """
        admin_only_fields: List[str] = [
            "is_active", "is_verified", "date_employment", "city", "company",
            "bitrix_id", "telegram_id", "gender", "role", "additional_role"
        ]
        employee_only_fields: List[str] = [
            "department_id", "group_id", "position", "user_email"
        ]

        if not hasattr(info, 'context') or info.context is None:
            return cls._validate_basic_fields(data, admin_only_fields + employee_only_fields)

        current_user = info.context.get('current_user')
        if not current_user:
            raise ValueError("Текущий пользователь не передан в контекст")

        is_admin = current_user.get('role') in settings.ADMIN_ROLES
        is_employee = current_user.get('role') in settings.EMPLOYEE_ROLES

        if not is_admin and not is_employee:
            return cls._validate_basic_fields(data, admin_only_fields + employee_only_fields)

        if not is_admin:
            return cls._validate_employee_fields(data, admin_only_fields)

        return data

    @staticmethod
    def _validate_basic_fields(data: Any, restricted_fields: List[str]) -> Any:
        """
        Проверяет доступ только к базовым полям
        """
        if isinstance(data, dict):
            for field in restricted_fields:
                if field in data and data[field] is not None:
                    raise ValueError(f"Нет доступа к обновлению поля {field}")
        else:
            for field in restricted_fields:
                if getattr(data, field, None) is not None:
                    raise ValueError(f"Нет доступа к обновлению поля {field}")
        return data

    @staticmethod
    def _validate_employee_fields(data: Any, admin_fields: List[str]) -> Any:
        """
        Проверяет доступ к полям для сотрудников
        """
        if isinstance(data, dict):
            for field in admin_fields:
                if field in data and data[field] is not None:
                    raise ValueError(f"Поле {field} может обновлять только администратор")
        else:
            for field in admin_fields:
                if getattr(data, field, None) is not None:
                    raise ValueError(f"Поле {field} может обновлять только администратор")
        return data

    @classmethod
    def validate_access(cls, info):
        """
        Проверяет доступ к полю
        """
        current_user = info.context.get('current_user')
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Требуется аутентификация"
            )

        is_admin = current_user.role in settings.ADMIN_ROLES
        is_employee = current_user.role in settings.EMPLOYEE_ROLES

        if not (is_admin or is_employee):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав"
            )
