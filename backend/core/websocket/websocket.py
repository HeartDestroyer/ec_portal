import json
import asyncio
from typing import Dict, Optional, Any, List
from fastapi import WebSocket, Depends
from datetime import datetime
from redis.asyncio import Redis

from core.extensions.redis import get_redis
from core.extensions.logger import logger
from core.config.config import settings
from .schemas import (
    MessageType, ModuleType, Channel, WebSocketMessage, 
    MessageHandler, ModuleManager, ConnectionInfo
)
from .connection_manager import ConnectionManager
from .channel_manager import ChannelManager
from .message_handler import MessageHandlerManager
from .module_manager import ModuleManagerRegistry
from .metrics import WebSocketMetrics

class ModularWebSocketManager:
    """
    Модульный WebSocket менеджер с поддержкой каналов\n
    Особенности:
        - Модульная архитектура (уведомления, чат, календарь)
        - Система каналов и подписок
        - Автоматическая регистрация обработчиков
        - Права доступа на уровне каналов
        - Горизонтальное масштабирование через Redis
    
    Методы:
        - `register_module` - Регистрация модуля
        - `register_message_handler` - Регистрация обработчика сообщений
        - `create_channel` - Создание канала
        - `subscribe_to_channel` - Подписка на канал
        - `unsubscribe_from_channel` - Отписка от канала
        - `connect` - Подключение клиента
        - `disconnect` - Отключение клиента
        - `send_to_channel` - Отправка сообщения в канал
        - `send_to_user` - Отправка сообщения пользователю
        - `send_to_connection` - Отправка сообщения конкретному соединению
        - `handle_message` - Обработка входящего сообщения
        - `_auto_subscribe_user_channels` - Автоматическая подписка на каналы пользователя
        - `_check_channel_permissions` - Проверка прав доступа к каналу
        - `_handle_system_message` - Обработка системных сообщений
        - `_handle_ping` - Обработка ping сообщений
        - `_handle_subscribe` - Обработка подписки на канал
        - `_handle_unsubscribe` - Обработка отписки от канала
        - `_ensure_background_tasks` - Запуск фоновых задач
        - `_redis_listener` - Слушатель Redis для горизонтального масштабирования
        - `_heartbeat` - Проверка активности соединений
        - `_handle_redis_message` - Обработка сообщений из Redis
    """
    def __init__(self, redis: Redis):
        """
        Инициализация WebSocket менеджера\n
        """
        self.redis = redis
        self.metrics = WebSocketMetrics()
        
        # Инициализация компонентов
        self.connection_manager = ConnectionManager(
            redis=self.redis,
            max_connections_per_user=settings.WEBSOCKET_MAX_CONNECTIONS_PER_USER,
            connection_timeout=settings.WEBSOCKET_CONNECTION_TIMEOUT
        )
        self.channel_manager = ChannelManager(self.redis)
        self.message_handler = MessageHandlerManager()
        self.module_registry = ModuleManagerRegistry()
        
        # Устанавливаем метрики для компонентов
        self.connection_manager.set_metrics(self.metrics)
        self.channel_manager.set_metrics(self.metrics)
        self.message_handler.set_metrics(self.metrics)
        self.module_registry.set_metrics(self.metrics)
        
        # Настройки
        self.websocket_ping_interval = settings.WEBSOCKET_PING_INTERVAL
        self.websocket_ping_timeout = settings.WEBSOCKET_PING_TIMEOUT
        self.websocket_close_timeout = settings.WEBSOCKET_CLOSE_TIMEOUT
        self.websocket_max_message_size = settings.WEBSOCKET_MAX_MESSAGE_SIZE
        self.websocket_max_queue_size = settings.WEBSOCKET_MAX_QUEUE_SIZE

        # Фоновые задачи
        self._redis_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """
        Инициализация менеджера
        """
        # Запускаем фоновые задачи
        await self._ensure_background_tasks()
        
        # Инициализируем модули
        from .modules.calendar import CalendarModuleManager
        from .modules.chat import ChatModuleManager
        
        calendar_manager = CalendarModuleManager(self.module_registry)
        chat_manager = ChatModuleManager(self.module_registry)
        
        self.module_registry.register(ModuleType.CALENDAR, calendar_manager)
        self.module_registry.register(ModuleType.CHAT, chat_manager)
        
        await calendar_manager.initialize()
        await chat_manager.initialize()
        
        logger.info("WebSocket менеджер инициализирован")

    def register_module(self, module_manager: ModuleManager) -> None:
        """
        Регистрация модуля\n
        `module_manager` - Менеджер модуля
        """
        self.module_registry.register(module_manager)
        self.metrics.increment_modules()

    def register_message_handler(self, message_type: str, handler: MessageHandler, module: Optional[ModuleType] = None) -> None:
        """
        Регистрация обработчика сообщений\n
        `message_type` - Тип сообщения\n
        `handler` - Обработчик сообщений\n
        `module` - Модуль
        """
        self.message_handler.register(message_type, handler, module)

    async def create_channel(self, module: ModuleType, name: str, permissions: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> Channel:
        """
        Создание канала\n
        `module` - Модуль\n
        `name` - Имя канала\n
        `permissions` - Права доступа\n
        `metadata` - Метаданные
        """
        channel = Channel(
            module=module,
            name=name,
            permissions=permissions or [],
            metadata=metadata or {}
        )
        
        self.channels[channel.full_name] = channel
        self.stats["channels_active"] = len(self.channels)
        
        # Уведомляем через Redis о создании канала
        await self._publish_channel_event("created", channel)
        
        logger.info(f"Создан канал: {channel.full_name}")
        return channel

    async def subscribe_to_channel(self, connection_id: str, channel_name: str, check_permissions: bool = True) -> bool:
        """
        Подписка соединения на канал\n
        `connection_id` - ID соединения\n
        `channel_name` - Имя канала\n
        `check_permissions` - Проверка прав доступа
        """
        if channel_name not in self.channels:
            logger.warning(f"Попытка подписки на несуществующий канал: {channel_name}")
            return False
            
        connection_info = self.connections.get(connection_id)
        if not connection_info:
            return False
            
        channel = self.channels[channel_name]
        
        # Проверка прав доступа
        if check_permissions and not await self._check_channel_permissions(connection_info, channel):
            logger.warning(f"Доступ запрещен: пользователь {connection_info.user_id} к каналу {channel_name}")
            return False
        
        # Подписываем
        self.channel_subscriptions[channel_name].add(connection_id)
        self.connection_channels[connection_id].add(channel_name)
        
        logger.info(f"Пользователь {connection_info.user_id} подписан на канал {channel_name}")
        
        # Уведомляем модуль о подписке
        if channel.module in self.modules:
            module_manager = self.modules[channel.module]
            await module_manager.on_connect(connection_info)
        
        return True

    async def unsubscribe_from_channel(self, connection_id: str, channel_name: str) -> bool:
        """
        Отписка от канала\n
        `connection_id` - ID соединения\n
        `channel_name` - Имя канала
        """
        if channel_name not in self.channels:
            return False
            
        self.channel_subscriptions[channel_name].discard(connection_id)
        self.connection_channels[connection_id].discard(channel_name)
        
        connection_info = self.connections.get(connection_id)
        if connection_info:
            logger.info(f"Пользователь {connection_info.user_id} отписан от канала {channel_name}")
        
        return True

    async def connect(self, websocket: WebSocket, user_id: str, initial_channels: Optional[List[str]] = None, user_agent: Optional[str] = None, ip_address: Optional[str] = None) -> str:
        """
        Подключение клиента\n
        `websocket` - WebSocket\n
        `user_id` - ID пользователя\n
        `initial_channels` - Инициальные каналы\n
        `user_agent` - User-Agent\n
        `ip_address` - IP-адрес
        """
        await websocket.accept()
        
        # Проверяем лимит соединений
        if await self.connection_manager.check_connection_limit(user_id):
            await websocket.close(code=4008, reason="Превышен лимит соединений")
            raise ConnectionError(f"Превышен лимит соединений для пользователя {user_id}")
        
        # Создаем соединение
        connection_info = ConnectionInfo(
            websocket=websocket,
            user_id=user_id,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        # Регистрируем соединение
        connection_id = await self.connection_manager.register_connection(connection_info)
        
        # Автоматическая подписка на каналы
        await self._auto_subscribe_user_channels(connection_info)
        
        # Подписка на дополнительные каналы
        if initial_channels:
            for channel_name in initial_channels:
                await self.channel_manager.subscribe(connection_id, channel_name)
        
        # Запускаем фоновые задачи
        await self._ensure_background_tasks()
        
        # Уведомляем модули
        await self.module_registry.on_connect(connection_info)
        
        self.metrics.increment_connections()
        logger.info(f"WebSocket подключен: user_id={user_id}, connection_id={connection_id}")
        
        return connection_id

    async def disconnect(self, websocket: WebSocket, reason: str = "client_disconnect") -> None:
        """
        Отключение клиента\n
        `websocket` - WebSocket\n
        `reason` - Причина отключения
        """
        connection_id = self.connection_manager.get_connection_id(websocket)
        if not connection_id:
            return
            
        connection_info = self.connection_manager.get_connection(connection_id)
        if not connection_info:
            return
            
        try:
            # Отписываем от каналов
            await self.channel_manager.unsubscribe_all(connection_id)
            
            # Уведомляем модули
            await self.module_registry.on_disconnect(connection_info)
            
            # Удаляем соединение
            await self.connection_manager.remove_connection(connection_id)
            
            logger.info(f"WebSocket отключен: user_id={connection_info.user_id}, connection_id={connection_id}, reason={reason}")
            
        except Exception as err:
            logger.error(f"Ошибка отключения WebSocket {connection_id}: {err}")

    async def handle_message(self, websocket: WebSocket, raw_message: dict) -> None:
        """
        Обработка входящего сообщения\n
        `websocket` - WebSocket\n
        `raw_message` - Сырое сообщение
        """
        connection_id = self.connection_manager.get_connection_id(websocket)
        if not connection_id:
            return
            
        connection_info = self.connection_manager.get_connection(connection_id)
        if not connection_info:
            return
        
        try:
            # Парсим сообщение
            message = WebSocketMessage(
                type=MessageType(raw_message.get("type", "unknown")),
                module=ModuleType(raw_message.get("module", "system")),
                channel=raw_message.get("channel"),
                data=raw_message.get("data", {}),
                sender_user=connection_info.user_id
            )
            
            self.metrics.increment_messages_received()
            
            # Обрабатываем системные сообщения
            if message.type in [MessageType.PING, MessageType.SUBSCRIBE, MessageType.UNSUBSCRIBE]:
                await self._handle_system_message(message, connection_info)
                return
            
            # Передаем в обработчики модулей
            await self.message_handler.handle(message, connection_info)
            
        except Exception as err:
            logger.error(f"Ошибка обработки сообщения от {connection_id}: {err}")

    async def send_to_channel(self, channel_name: str, message: WebSocketMessage, exclude_connection: Optional[str] = None) -> int:
        """
        Отправка сообщения в канал\n
        `channel_name` - Имя канала\n
        `message` - Сообщение\n
        `exclude_connection` - Исключить соединение
        """
        return await self.channel_manager.broadcast(channel_name, message, exclude_connection)

    async def send_to_user(self, user_id: str, message: WebSocketMessage, module_filter: Optional[ModuleType] = None) -> int:
        """
        Отправка сообщения пользователю\n
        `user_id` - ID пользователя\n
        `message` - Сообщение\n
        `module_filter` - Фильтр модулей
        """
        return await self.connection_manager.send_to_user(user_id, message, module_filter)

    async def send_to_connection(self, connection_id: str, message: dict) -> bool:
        """
        Отправка сообщения конкретному соединению\n
        `connection_id` - ID соединения\n
        `message` - Сообщение
        """
        return await self.connection_manager.send(connection_id, message)

    # Приватные методы

    async def _auto_subscribe_user_channels(self, connection_info: ConnectionInfo) -> None:
        """
        Автоматическая подписка на каналы пользователя\n
        `connection_info` - Информация о соединении
        """
        user_id = connection_info.user_id
        
        for module_manager in self.module_registry.get_managers():
            try:
                channels = await module_manager.get_user_channels(user_id)
                for channel in channels:
                    if not await self.channel_manager.exists(channel.full_name):
                        await self.channel_manager.create(
                            channel.module,
                            channel.name,
                            channel.permissions,
                            channel.metadata
                        )
                    
                    await self.channel_manager.subscribe(
                        connection_info.connection_id,
                        channel.full_name,
                        check_permissions=False
                    )
            except Exception as err:
                logger.error(f"Ошибка автоподписки для модуля {module_manager.module_type.value}: {err}")

    async def _handle_system_message(self, message: WebSocketMessage, connection_info: ConnectionInfo) -> None:
        """
        Обработка системных сообщений\n
        `message` - Сообщение\n
        `connection_info` - Информация о соединении
        """
        handlers = {
            MessageType.PING: self._handle_ping,
            MessageType.SUBSCRIBE: self._handle_subscribe,
            MessageType.UNSUBSCRIBE: self._handle_unsubscribe
        }
        
        handler = handlers.get(message.type)
        if handler:
            await handler(message, connection_info)

    async def _handle_ping(self, message: WebSocketMessage, connection_info: ConnectionInfo) -> None:
        """
        Обработка ping сообщений\n
        `message` - Сообщение\n
        `connection_info` - Информация о соединении
        """
        connection_info.last_ping = datetime.utcnow()
        
        pong_response = WebSocketMessage(
            type=MessageType.PONG,
            module=ModuleType.SYSTEM,
            data={
                "timestamp": datetime.utcnow().isoformat(),
                "connection_id": connection_info.connection_id
            }
        )
        
        await self.send_to_connection(connection_info.connection_id, pong_response.__dict__)

    async def _handle_subscribe(self, message: WebSocketMessage, connection_info: ConnectionInfo) -> None:
        """
        Обработка подписки на канал\n
        `message` - Сообщение\n
        `connection_info` - Информация о соединении
        """
        channel_name = message.data.get("channel")
        if not channel_name:
            return
            
        success = await self.channel_manager.subscribe(
            connection_info.connection_id,
            channel_name
        )
        
        response = WebSocketMessage(
            type=MessageType.SUBSCRIBE if success else MessageType.ERROR,
            module=ModuleType.SYSTEM,
            data={
                "channel": channel_name,
                "success": success,
                "message": "Подписка успешна" if success else "Ошибка подписки"
            }
        )
        
        await self.send_to_connection(connection_info.connection_id, response.__dict__)

    async def _handle_unsubscribe(self, message: WebSocketMessage, connection_info: ConnectionInfo) -> None:
        """
        Обработка отписки от канала\n
        `message` - Сообщение\n
        `connection_info` - Информация о соединении
        """
        channel_name = message.data.get("channel")
        if not channel_name:
            return
            
        success = await self.channel_manager.unsubscribe(
            connection_info.connection_id,
            channel_name
        )
        
        response = WebSocketMessage(
            type=MessageType.UNSUBSCRIBE,
            module=ModuleType.SYSTEM,
            data={
                "channel": channel_name,
                "success": success
            }
        )
        
        await self.send_to_connection(connection_info.connection_id, response.__dict__)

    async def _ensure_background_tasks(self) -> None:
        """
        Запуск фоновых задач\n
        """
        if not self._redis_task:
            self._redis_task = asyncio.create_task(self._redis_listener())
        if not self._heartbeat_task:
            self._heartbeat_task = asyncio.create_task(self._heartbeat())

    async def _redis_listener(self) -> None:
        """
        Слушатель Redis для горизонтального масштабирования\n
        """
        try:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe("websocket:*")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await self._handle_redis_message(message)
        except Exception as err:
            logger.error(f"Ошибка в Redis listener: {err}")

    async def _heartbeat(self) -> None:
        """
        Проверка активности соединений\n
        """
        while True:
            try:
                await asyncio.sleep(self.websocket_ping_interval)
                await self.connection_manager.check_connections()
            except Exception as err:
                logger.error(f"Ошибка в heartbeat: {err}")

    async def _handle_redis_message(self, message: dict) -> None:
        """Обработка сообщений из Redis\n
        `message` - Сообщение
        """
        try:
            channel = message["channel"].decode()
            data = json.loads(message["data"])
            
            if channel.startswith("websocket:channel:"):
                await self.channel_manager.handle_redis_message(channel, data)
            elif channel.startswith("websocket:user:"):
                await self.connection_manager.handle_redis_message(channel, data)
        except Exception as err:
            logger.error(f"Ошибка обработки Redis сообщения: {err}")

websocket_manager = ModularWebSocketManager(redis=get_redis())

