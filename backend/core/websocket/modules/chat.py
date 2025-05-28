from typing import Dict, List, Optional, Set
from datetime import datetime
from core.extensions.logger import logger
from ..schemas import ModuleType, WebSocketMessage, MessageType, Channel
from ..module_manager import ModuleManagerRegistry

class ChatModuleManager:
    """
    Менеджер модуля чата для WebSocket\n
    Методы:
        - `initialize` - Инициализация модуля
        - `create_default_channels` - Создание базовых каналов
        - `create_channel` - Создание канала
        - `handle_chat_message` - Обработка сообщений чата
        - `handle_chat_action` - Обработка действий в чате
        - `_handle_join_room` - Обработка присоединения к комнате

    TODO:
        - Реализовать проверку прав доступа `_check_channel_permissions`
        - Добавить логику проверки прав доступа к каналу `_check_channel_permissions`
    """
    def __init__(self, module_registry: ModuleManagerRegistry):
        self.module_type = ModuleType.CHAT
        self.module_registry = module_registry
        self._channels: Dict[str, Channel] = {}
        self._user_rooms: Dict[int, Set[str]] = {}  # user_id -> set of room_ids
        
    async def initialize(self) -> None:
        """
        Инициализация модуля
        """
        # Регистрация обработчиков сообщений
        self.module_registry.register_message_handler(
            MessageType.CHAT_MESSAGE,
            self.handle_chat_message,
            self.module_type
        )
        
        self.module_registry.register_message_handler(
            MessageType.CHAT_ACTION,
            self.handle_chat_action,
            self.module_type
        )
        
        # Создание базовых каналов
        await self.create_default_channels()
        
    async def create_default_channels(self) -> None:
        """
        Создание базовых каналов чата
        """
        channels = [
            Channel(
                module=self.module_type,
                name="general",
                permissions=["chat:view"],
                metadata={"type": "public"}
            ),
            Channel(
                module=self.module_type,
                name="support",
                permissions=["chat:view"],
                metadata={"type": "public"}
            )
        ]
        
        for channel in channels:
            await self.create_channel(channel)
            
    async def create_channel(self, channel: Channel) -> None:
        """
        Создание канала чата\n
        `channel` - Канал чата
        """
        self._channels[channel.full_name] = channel
        logger.info(f"Создан канал чата: {channel.full_name}")
        
    async def create_private_room(self, user_ids: List[int], room_name: str) -> str:
        """
        Создание приватной комнаты\n
        `user_ids` - ID пользователей\n
        `room_name` - Имя комнаты
        Возвращает ID комнаты
        """
        room_id = f"private_{room_name}_{datetime.utcnow().timestamp()}"
        
        channel = Channel(
            module=self.module_type,
            name=room_id,
            permissions=[f"chat:room:{room_id}"],
            metadata={
                "type": "private",
                "users": user_ids,
                "name": room_name
            }
        )
        
        await self.create_channel(channel)
        
        # Добавляем комнату пользователям
        for user_id in user_ids:
            if user_id not in self._user_rooms:
                self._user_rooms[user_id] = set()
            self._user_rooms[user_id].add(room_id)
            
        return room_id
        
    async def handle_chat_message(self, message: WebSocketMessage) -> None:
        """
        Обработка сообщений чата\n
        `message` - Сообщение
        """
        try:
            channel_id = message.channel
            if not channel_id or channel_id not in self._channels:
                logger.warning(f"Попытка отправить сообщение в несуществующий канал: {channel_id}")
                return
                
            # Проверка прав доступа
            if not await self._check_channel_permissions(message.sender_user, channel_id):
                logger.warning(f"Отказано в доступе к каналу {channel_id} для пользователя {message.sender_user}")
                return
                
            # Отправка сообщения в канал
            await self.module_registry.send_to_channel(channel_id, message)
            
        except Exception as err:
            logger.error(f"Ошибка обработки сообщения чата: {err}")
            
    async def handle_chat_action(self, message: WebSocketMessage) -> None:
        """
        Обработка действий в чате\n
        `message` - Сообщение
        """
        try:
            action = message.data.get("action")
            if action == "join":
                await self._handle_join_room(message)
            elif action == "leave":
                await self._handle_leave_room(message)
            elif action == "create_room":
                await self._handle_create_room(message)
            else:
                logger.warning(f"Неизвестное действие чата: {action}")
                
        except Exception as err:
            logger.error(f"Ошибка обработки действия чата: {err}")
            
    async def _handle_join_room(self, message: WebSocketMessage) -> None:
        """
        Обработка присоединения к комнате\n
        `message` - Сообщение
        """
        room_id = message.data.get("room_id")
        if not room_id or room_id not in self._channels:
            return
            
        user_id = message.sender_user
        if user_id not in self._user_rooms:
            self._user_rooms[user_id] = set()
            
        self._user_rooms[user_id].add(room_id)
        
        # Уведомление о присоединении
        notification = WebSocketMessage(
            type=MessageType.CHAT_ACTION,
            module=self.module_type,
            channel=room_id,
            data={
                "action": "user_joined",
                "user_id": user_id
            }
        )
        
        await self.module_registry.send_to_channel(room_id, notification)
        
    async def _handle_leave_room(self, message: WebSocketMessage) -> None:
        """
        Обработка выхода из комнаты\n
        `message` - Сообщение
        """
        room_id = message.data.get("room_id")
        if not room_id:
            return
            
        user_id = message.sender_user
        if user_id in self._user_rooms:
            self._user_rooms[user_id].discard(room_id)
            
        # Уведомление о выходе
        notification = WebSocketMessage(
            type=MessageType.CHAT_ACTION,
            module=self.module_type,
            channel=room_id,
            data={
                "action": "user_left",
                "user_id": user_id
            }
        )
        
        await self.module_registry.send_to_channel(room_id, notification)
        
    async def _handle_create_room(self, message: WebSocketMessage) -> None:
        """
        Обработка создания комнаты\n
        `message` - Сообщение
        """
        room_name = message.data.get("room_name")
        user_ids = message.data.get("users", [])
        
        if not room_name or not user_ids:
            return
            
        room_id = await self.create_private_room(user_ids, room_name)
        
        # Уведомление о создании комнаты
        notification = WebSocketMessage(
            type=MessageType.CHAT_ACTION,
            module=self.module_type,
            data={
                "action": "room_created",
                "room_id": room_id,
                "room_name": room_name
            }
        )
        
        for user_id in user_ids:
            await self.module_registry.send_to_user(user_id, notification)
            
    async def _check_channel_permissions(self, user_id: int, channel_id: str) -> bool:
        """
        Проверка прав доступа к каналу\n
        `user_id` - ID пользователя\n
        `channel_id` - ID канала
        Возвращает True, если пользователь имеет доступ к каналу, иначе False
        """
        # TODO: Реализовать проверку прав доступа
        return True
        
    async def on_connect(self, connection_id: str, user_id: Optional[int] = None) -> None:
        """Обработка подключения пользователя\n
        `connection_id` - ID соединения\n
        `user_id` - ID пользователя
        """
        if user_id:
            # Подписка на каналы чата пользователя
            for channel in self._channels.values():
                if await self._check_channel_permissions(user_id, channel.full_name):
                    await self.module_registry.subscribe_to_channel(
                        connection_id,
                        channel.full_name
                    )
                    
    async def on_disconnect(self, connection_id: str, user_id: Optional[int] = None) -> None:
        """Обработка отключения пользователя\n
        `connection_id` - ID соединения\n
        `user_id` - ID пользователя
        """
        # Отписка от всех каналов чата
        for channel in self._channels.values():
            await self.module_registry.unsubscribe_from_channel(
                connection_id,
                channel.full_name
            )
