from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, ClassVar, Type
from datetime import datetime
import copy
import uuid
from pydantic.types import UUID4

class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            uuid.UUID: str,
            UUID4: str
        }
    )

class TokenFactory:
    """
    Фабрика для создания токенов\n
    Реализует паттерн Factory для создания объектов TokenPayload
    """
    
    @staticmethod
    def create_from_dict(data: Dict[str, Any]) -> 'TokenPayload':
        """
        Создает TokenPayload из словаря\n
        `data` - Словарь с данными для создания токена
        """
        data_copy = copy.deepcopy(data)
        
        # Проверяем, что в словаре есть обязательные поля
        valid_fields = {"user_id", "session_id", "token_type", "exp", "role"}
        filtered_data = {k: v for k, v in data_copy.items() if k in valid_fields}
        
        # UUID -> строки
        if "user_id" in filtered_data:
            filtered_data["user_id"] = str(filtered_data["user_id"])
        if "session_id" in filtered_data:
            filtered_data["session_id"] = str(filtered_data["session_id"])
            
        return TokenPayload(
            user_id=filtered_data.get("user_id", ""),
            session_id=filtered_data.get("session_id", ""),
            token_type=filtered_data.get("token_type"),
            exp=filtered_data.get("exp"),
            role=filtered_data.get("role")
        )
    
    @staticmethod
    def create_from_user_session(
        user_id: str,
        session_id: str,
        token_type: Optional[str] = None,
        exp: Optional[int] = None,
        role: Optional[str] = None
    ) -> 'TokenPayload':
        """
        Создает TokenPayload из параметров пользователя и сессии\n
        `user_id` - ID пользователя\n
        `session_id` - ID сессии\n
        `token_type` - Тип токена аутентификации\n
        `exp` - Время истечения токена\n
        `role` - Роль пользователя
        """
        return TokenPayload(
            user_id=str(user_id),
            session_id=str(session_id),
            token_type=token_type,
            exp=exp,
            role=role
        )
    
class TokenPayload(BaseSchema):
    """
    Данные для токена аутентификации
    """
    user_id: str = Field(..., description="ID пользователя")
    session_id: str = Field(..., description="ID сессии пользователя")
    token_type: Optional[str] = Field(None, description="Тип токена аутентификации")
    exp: Optional[int] = Field(None, description="Время истечения токена")
    role: Optional[str] = Field(None, description="Роль пользователя")
    
    # Связь с фабрикой для удобства создания
    factory: ClassVar[Type[TokenFactory]] = TokenFactory
        
class Tokens(BaseSchema):
    """
    Токены для аутентификации
    """
    access_token: str = Field(..., description="Access токен для аутентификации")
    refresh_token: str = Field(..., description="Refresh токен для аутентификации")

# Стандартная схема для ответа на запросы
class MessageResponse(BaseSchema):
    """
    Стандартная схема для ответа на запросы\n
    Сообщение и время отправки
    """
    message: str = Field(..., description="Сообщение")
    status: Optional[bool] = Field(True, description="Статус")
    data: Optional[Dict] = Field(default=None, description="Дополнительные данные")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Время отправки сообщения")
