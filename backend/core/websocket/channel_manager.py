from typing import Dict, Set, Optional, Any
from collections import defaultdict
from redis.asyncio import Redis
import json

from core.extensions.logger import logger
from .schemas import Channel, WebSocketMessage

class ChannelManager:
    """
    Менеджер каналов WebSocket\n
    Методы:
        - `create` - Создание нового канала
        - `exists` - Проверка существования канала
        - `subscribe` - Подписка на канал
        - `unsubscribe` - Отписка от канала
        - `unsubscribe_all` - Отписка от всех каналов
        - `broadcast` - Отправка сообщения всем подписчикам канала

    TODO: 
        - Реализовать проверку прав доступа `_check_permissions`
        - Реализовать отправку сообщения подписчикам `broadcast`
        - Реализовать обработку сообщений из Redis `handle_redis_message`
    """
    def __init__(self, redis: Redis):
        self._channels: Dict[str, Channel] = {}
        self._subscriptions: Dict[str, Set[str]] = defaultdict(set)  # channel_id -> set of connection_ids
        self._redis = redis
        self._metrics = None  # Будет установлен извне

    def set_metrics(self, metrics) -> None:
        """
        Установка объекта метрик\n
        `metrics` - Объект метрик
        """
        self._metrics = metrics

    async def create(self, channel: Channel) -> None:
        """
        Создание нового канала\n
        `channel` - Объект канала
        """
        if channel.id in self._channels:
            logger.warning(f"Канал {channel.id} уже существует")
            return

        self._channels[channel.id] = channel
        if self._metrics:
            self._metrics.increment_channels()
        
        # Публикация события создания канала
        await self._publish_channel_event("channel_created", channel)
        logger.info(f"Создан канал: {channel.id}")

    def exists(self, channel_id: str) -> bool:
        """
        Проверка существования канала\n
        `channel_id` - ID канала\n
        Возвращает True если канал существует
        """
        return channel_id in self._channels

    async def subscribe(self, connection_id: str, channel_id: str) -> bool:
        """
        Подписка на канал\n
        `connection_id` - ID соединения\n
        `channel_id` - ID канала\n
        Возвращает True если подписка успешна
        """
        if not self.exists(channel_id):
            logger.warning(f"Попытка подписки на несуществующий канал: {channel_id}")
            return False

        channel = self._channels[channel_id]
        if not await self._check_permissions(connection_id, channel):
            logger.warning(f"Отказано в доступе к каналу {channel_id} для соединения {connection_id}")
            return False

        self._subscriptions[channel_id].add(connection_id)
        await self._publish_channel_event("channel_subscribed", channel, connection_id)
        logger.info(f"Соединение {connection_id} подписано на канал {channel_id}")
        return True

    async def unsubscribe(self, connection_id: str, channel_id: str) -> None:
        """
        Отписка от канала\n
        `connection_id` - ID соединения\n
        `channel_id` - ID канала
        """
        if channel_id in self._subscriptions:
            self._subscriptions[channel_id].discard(connection_id)
            await self._publish_channel_event("channel_unsubscribed", self._channels[channel_id], connection_id)
            logger.info(f"Соединение {connection_id} отписано от канала {channel_id}")

    async def unsubscribe_all(self, connection_id: str) -> None:
        """
        Отписка от всех каналов\n
        `connection_id` - ID соединения
        """
        for channel_id in list(self._subscriptions.keys()):
            await self.unsubscribe(connection_id, channel_id)

    async def broadcast(self, channel_id: str, message: WebSocketMessage, exclude_connection: Optional[str] = None) -> None:
        """
        Отправка сообщения всем подписчикам канала\n
        `channel_id` - ID канала\n
        `message` - Сообщение для отправки\n
        `exclude_connection` - ID соединения для исключения
        """
        if not self.exists(channel_id):
            logger.warning(f"Попытка отправки в несуществующий канал: {channel_id}")
            return

        subscribers = self._subscriptions.get(channel_id, set())
        if exclude_connection:
            subscribers.discard(exclude_connection)

        if not subscribers:
            logger.debug(f"Нет подписчиков в канале {channel_id}")
            return

        # Публикация сообщения в Redis для других инстансов
        await self._publish_message(channel_id, message)

        if self._metrics:
            self._metrics.increment_messages_sent()

    async def _check_permissions(self, connection_id: str, channel: Channel) -> bool:
        """
        Проверка прав доступа к каналу\n
        `connection_id` - ID соединения\n
        `channel` - Объект канала\n
        Возвращает True если доступ разрешен
        """
        # TODO: Реализовать проверку прав доступа
        return True

    async def _publish_channel_event(self, event_type: str, channel: Channel, connection_id: Optional[str] = None) -> None:
        """
        Публикация события канала в Redis\n
        `event_type` - Тип события\n
        `channel` - Объект канала\n
        `connection_id` - ID соединения (опционально)
        """
        event = {
            "type": event_type,
            "channel": channel.dict(),
            "connection_id": connection_id
        }
        await self._redis.publish("websocket:channel_events", json.dumps(event))

    async def _publish_message(self, channel_id: str, message: WebSocketMessage) -> None:
        """
        Публикация сообщения в Redis\n
        `channel_id` - ID канала\n
        `message` - Сообщение для публикации
        """
        event = {
            "channel_id": channel_id,
            "message": message.dict()
        }
        await self._redis.publish("websocket:messages", json.dumps(event))

    async def handle_redis_message(self, message: Dict[str, Any]) -> None:
        """
        Обработка сообщения из Redis\n
        `message` - Сообщение из Redis
        """
        if "channel_id" in message and "message" in message:
            channel_id = message["channel_id"]
            if self.exists(channel_id):
                subscribers = self._subscriptions.get(channel_id, set())
                # TODO: Реализовать отправку сообщения подписчикам
