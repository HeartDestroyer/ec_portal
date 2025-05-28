from typing import TypeVar, Protocol, Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from pydantic import Field, BaseModel

UserIdType = TypeVar('UserIdType', bound=str)

class MessageType(str, Enum):
    """
    Типы WebSocket сообщений:
        - Системные - `ping`, `pong`, `subscribe`, `unsubscribe`, `error`
        - Уведомления - `notification`, `notification_read`
        - Чат - `chat_message`, `chat_join_room`, `chat_leave_room`, `chat_typing`
        - Календарь - `calendar_booking`, `calendar_update`, `calendar_reminder`
        - Новые типы сообщений - `calendar_event`, `chat_action`
    """

    # Системные
    PING = "ping"
    PONG = "pong"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    ERROR = "error"
    
    # Уведомления
    NOTIFICATION = "notification"
    NOTIFICATION_READ = "notification_read"
    
    # Чат
    CHAT_MESSAGE = "chat_message"
    CHAT_JOIN_ROOM = "chat_join_room"
    CHAT_LEAVE_ROOM = "chat_leave_room"
    CHAT_TYPING = "chat_typing"
    
    # Календарь
    CALENDAR_BOOKING = "calendar_booking"
    CALENDAR_UPDATE = "calendar_update"
    CALENDAR_REMINDER = "calendar_reminder"

    # Новые типы сообщений
    CALENDAR_EVENT = "calendar_event"
    CHAT_ACTION = "chat_action"

class ModuleType(str, Enum):
    """
    Модули системы
        - Уведомления - `notifications`
        - Чат - `chat`
        - Календарь - `calendar`
        - Система - `system`
    """
    NOTIFICATIONS = "notifications"
    CHAT = "chat"
    CALENDAR = "calendar"
    SYSTEM = "system"

@dataclass
class Channel:
    """
    Канал для группировки соединений\n
    `module` - Модуль\n
    `name` - Имя канала\n
    `permissions` - Права доступа\n
    `metadata` - Метаданные
    """
    module: ModuleType = Field(..., description="Модуль")
    name: str = Field(..., description="Имя канала")
    permissions: List[str] = Field(None, description="Права доступа")
    metadata: Dict[str, Any] = Field(None, description="Метаданные")
    
    @property
    def full_name(self) -> str:
        return f"{self.module.value}:{self.name}"

class WebSocketMessage(BaseModel):
    """
    Модель сообщения WebSocket\n
    `type` - Тип сообщения\n
    `module` - Модуль\n
    `channel` - Канал\n
    `data` - Данные\n
    `sender_user` - Отправитель\n
    `timestamp` - Время отправки\n
    `message_id` - ID сообщения
    """
    type: MessageType = Field(..., description="Тип сообщения")
    module: ModuleType = ModuleType.SYSTEM
    channel: Optional[str] = Field(None, description="Канал")   
    data: Dict[str, Any] = Field(None, description="Данные")
    sender_user: Optional[int] = Field(None, description="Отправитель")
    timestamp: datetime = Field(None, description="Время отправки")
    message_id: Optional[str] = Field(None, description="ID сообщения")

class ConnectionInfo(BaseModel):
    """Информация о соединении\n
    `connection_id` - ID соединения\n
    `user_id` - ID пользователя\n
    `user_agent` - User-Agent\n
    `ip_address` - IP-адрес\n
    `last_ping` - Время последнего пинга\n
    `channels` - Каналы
    """
    connection_id: str = Field(..., description="ID соединения")    
    user_id: Optional[int] = Field(None, description="ID пользователя")
    user_agent: Optional[str] = Field(None, description="User-Agent")
    ip_address: Optional[str] = Field(None, description="IP-адрес")
    last_ping: Optional[datetime] = Field(None, description="Время последнего пинга")
    channels: List[str] = Field(..., description="Каналы")

class MessageHandler(Protocol):
    """
    Протокол для обработчиков сообщений модулей
    Методы:
        - `handle_message` - Обработка сообщения модулем
    """
    async def handle_message(self, message: WebSocketMessage, connection_info: 'ConnectionInfo') -> Optional[WebSocketMessage]:
        """
        Обработка сообщения модулем\n
        `message` - сообщение\n
        `connection_info` - информация о подключении
        """
        pass

class ModuleManager(Protocol):
    """
    Протокол для менеджеров модулей
    Методы:
        - `on_connect` - Вызывается при подключении пользователя
        - `on_disconnect` - Вызывается при отключении пользователя
        - `get_user_channels` - Получение каналов пользователя для модуля
    """
    module_type: ModuleType
    
    async def on_connect(self, connection_info: 'ConnectionInfo') -> None:
        """
        Вызывается при подключении пользователя\n
        `connection_info` - информация о подключении
        """
        pass
    
    async def on_disconnect(self, connection_info: 'ConnectionInfo') -> None:
        """
        Вызывается при отключении пользователя\n
        `connection_info` - информация о подключении
        """
        pass
    
    async def get_user_channels(self, user_id: str) -> List[Channel]:
        """
        Получение каналов пользователя для модуля\n
        `user_id` - ID пользователя
        """
        pass
