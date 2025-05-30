# backend/api/v1/session/schemas/response_schemas.py - Схемы для ответов на запросы на сессии пользователей

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from pydantic.types import UUID4
from datetime import datetime
import uuid

BASE_CONFIG = ConfigDict(
    from_attributes=True,
    json_encoders={
        uuid.UUID: str,
        UUID4: str
    }
)

class SessionResponse(BaseModel):
    """
    Схема для получения информации о сессии\n
    Реализована с пагинацией и поиском по имени пользователя
        - `id` - ID сессии
        - `user_id` - ID пользователя
        - `user_name` - Имя пользователя
        - `device` - Устройство
        - `browser` - Браузер
        - `os` - Операционная система
        - `platform` - Платформа
        - `location` - Местоположение
        - `ip_address` - IP адрес
        - `last_activity` - Последняя активность
        - `created_at` - Дата создания
        - `is_active` - Активная ли сессия
        - `is_current` - Текущая ли сессия
    """
    model_config = BASE_CONFIG

    id: UUID4 = Field(None, description="ID сессии")
    user_id: UUID4 = Field(None, description="ID пользователя")
    user_name: str = Field(None, description="Имя пользователя")
    device: Optional[str] = Field(None, description="Устройство")
    browser: Optional[str] = Field(None, description="Браузер")
    os: Optional[str] = Field(None, description="Операционная система")
    platform: Optional[str] = Field(None, description="Платформа")
    location: Optional[str] = Field(None, description="Местоположение") 
    ip_address: Optional[str] = Field(None, description="IP адрес")
    last_activity: Optional[datetime] = Field(None, description="Последняя активность")
    created_at: Optional[datetime] = Field(None, description="Дата создания")
    is_active: Optional[bool] = Field(None, description="Активная ли сессия")
    is_current: Optional[bool] = Field(None, description="Текущая ли сессия")

class SessionsPage(BaseModel):
    """
    Схема для получения списка сессий с пагинацией и информацией о браузере, устройстве и геолокации пользователя в момент входа в систему
        - `total` - Общее количество сессий
        - `page` - Текущая страница
        - `page_size` - Размер страницы
        - `pages` - Общее количество страниц
        - `sessions` - Список сессий
    """
    model_config = BASE_CONFIG

    total: int = Field(description="Общее количество сессий")
    page: int = Field(description="Текущая страница")
    page_size: int = Field(description="Размер страницы")
    pages: int = Field(description="Общее количество страниц")
    sessions: List[SessionResponse] = Field(description="Список сессий")

class UserAgentInfo(BaseModel):
    """
    Схема для получения информации о браузере, устройстве и геолокации пользователя в момент входа в систему
        - `browser` - Браузер
        - `os` - Операционная система
        - `platform` - Платформа
        - `device` - Устройство
        - `location` - Геолокация
        - `ip_address` - IP-адрес (локальная сеть, если нет IP-адреса)
    """
    model_config = BASE_CONFIG

    browser: str = Field(description="Браузер")
    os: str = Field(description="Операционная система")
    platform: str = Field(description="Платформа")
    device: str = Field(description="Устройство")
    location: str = Field(description="Геолокация")
    ip_address: str = Field(description="IP-адрес (локальная сеть, если нет IP-адреса)")
