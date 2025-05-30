# backend/api/v1/session/schemas/request_schemas.py - Схемы для запросов на сессии пользователей

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from pydantic.types import UUID4
import uuid

BASE_CONFIG = ConfigDict(
    from_attributes=True,
    json_encoders={
        uuid.UUID: str,
        UUID4: str
    }
)

class SessionFilter(BaseModel):
    """
    Схема для фильтрации сессий с пагинацией и поиском по имени пользователя
        - `user_id` - ID пользователя
        - `user_name` - Имя пользователя
        - `is_active` - Активная ли сессия
        - `page` - Номер страницы
        - `page_size` - Размер страницы
    """
    model_config = BASE_CONFIG

    user_id: Optional[str] = Field(None, description="ID пользователя")
    user_name: Optional[str] = Field(None, description="Имя пользователя")
    is_active: Optional[bool] = Field(None, description="Активная ли сессия")
    page: int = Field(default=1, ge=1, description="Номер страницы")
    page_size: int = Field(default=10, ge=1, le=100, description="Размер страницы")
