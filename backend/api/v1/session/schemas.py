from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from pydantic.types import UUID4
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
    Схема для получения информации о сессии с пагинацией и поиском по имени пользователя
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

class SessionFilter(BaseModel):
    """
    Схема для фильтрации сессий с пагинацией и поиском по имени пользователя
    """
    model_config = BASE_CONFIG

    user_id: Optional[str] = Field(None, description="ID пользователя")
    user_name: Optional[str] = Field(None, description="Имя пользователя")
    is_active: Optional[bool] = Field(None, description="Активная ли сессия")
    page: int = Field(default=1, ge=1, description="Номер страницы")
    page_size: int = Field(default=10, ge=1, le=100, description="Размер страницы")

class SessionsPage(BaseModel):
    """
    Схема для получения списка сессий с пагинацией и информацией о браузере, устройстве и геолокации пользователя в момент входа в систему
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
    """
    model_config = BASE_CONFIG

    browser: str = Field(description="Браузер")
    os: str = Field(description="Операционная система")
    platform: str = Field(description="Платформа")
    device: str = Field(description="Устройство")
    location: str = Field(description="Геолокация")
    ip_address: str = Field(description="IP-адрес (локальная сеть, если нет IP-адреса)")

