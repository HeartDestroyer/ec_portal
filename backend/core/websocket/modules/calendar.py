from typing import Dict, Optional
from core.extensions.logger import logger
from core.websocket.schemas import ModuleType, WebSocketMessage, MessageType, Channel
from core.websocket.module_manager import ModuleManagerRegistry

class CalendarModuleManager:
    """
    Менеджер модуля календаря для WebSocket\n
    Методы:
        - `initialize` - Инициализация модуля
        - `create_default_channels` - Создание базовых каналов
        - `create_channel` - Создание канала
        - `handle_calendar_event` - Обработка событий календаря
        - `_handle_event_creation` - Обработка создания события
        - `_handle_event_update` - Обработка обновления события
        - `_handle_event_deletion` - Обработка удаления события
        - `on_connect` - Обработка подключения пользователя
        - `on_disconnect` - Обработка отключения пользователя

    TODO:
        - Добавить логику создания события `_handle_event_creation`
        - Добавить логику обновления события `_handle_event_update`
        - Добавить логику удаления события `_handle_event_deletion`
    """
    def __init__(self, module_registry: ModuleManagerRegistry):
        self.module_type = ModuleType.CALENDAR
        self.module_registry = module_registry
        self._channels: Dict[str, Channel] = {}
        
    async def initialize(self) -> None:
        """
        Инициализация модуля
        """
        # Регистрация обработчиков сообщений
        self.module_registry.register_message_handler(
            MessageType.CALENDAR_EVENT,
            self.handle_calendar_event,
            self.module_type
        )
        
        # Создание базовых каналов
        await self.create_default_channels()
        
    async def create_default_channels(self) -> None:
        """
        Создание базовых каналов календаря
        """
        channels = [
            Channel(
                module=self.module_type,
                name="events",
                permissions=["calendar:view"],
                metadata={"type": "events"}
            ),
            Channel(
                module=self.module_type,
                name="reminders",
                permissions=["calendar:view"],
                metadata={"type": "reminders"}
            )
        ]
        
        for channel in channels:
            await self.create_channel(channel)
            
    async def create_channel(self, channel: Channel) -> None:
        """
        Создание канала календаря\n
        `channel` - Канал календаря
        """
        self._channels[channel.full_name] = channel
        logger.info(f"Создан канал календаря: {channel.full_name}")
        
    async def handle_calendar_event(self, message: WebSocketMessage) -> None:
        """
        Обработка событий календаря\n
        `message` - Сообщение
        """
        try:
            event_type = message.data.get("event_type")
            event_data = message.data.get("data", {})
            
            if event_type == "create":
                await self._handle_event_creation(event_data)
            elif event_type == "update":
                await self._handle_event_update(event_data)
            elif event_type == "delete":
                await self._handle_event_deletion(event_data)
            else:
                logger.warning(f"Неизвестный тип события календаря: {event_type}")
                
        except Exception as err:
            logger.error(f"Ошибка обработки события календаря: {err}")
            
    async def _handle_event_creation(self, event_data: Dict) -> None:
        """
        Обработка создания события\n
        `event_data` - Данные события
        """
        # TODO: Реализовать логику создания события
        pass
        
    async def _handle_event_update(self, event_data: Dict) -> None:
        """
        Обработка обновления события\n
        `event_data` - Данные события
        """
        # TODO: Реализовать логику обновления события
        pass
        
    async def _handle_event_deletion(self, event_data: Dict) -> None:
        """
        Обработка удаления события\n
        `event_data` - Данные события
        """
        # TODO: Реализовать логику удаления события
        pass
        
    async def on_connect(self, connection_id: str, user_id: Optional[int] = None) -> None:
        """
        Обработка подключения пользователя\n
        `connection_id` - ID соединения\n
        `user_id` - ID пользователя
        """
        if user_id:
            # Подписка на каналы календаря пользователя
            for channel in self._channels.values():
                await self.module_registry.subscribe_to_channel(
                    connection_id,
                    channel.full_name
                )
                
    async def on_disconnect(self, connection_id: str, user_id: Optional[int] = None) -> None:
        """
        Обработка отключения пользователя\n
        `connection_id` - ID соединения\n
        `user_id` - ID пользователя
        """
        # Отписка от всех каналов календаря
        for channel in self._channels.values():
            await self.module_registry.unsubscribe_from_channel(
                connection_id,
                channel.full_name
            )
