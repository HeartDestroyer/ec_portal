from typing import Dict, Set, Optional, Any
from fastapi import WebSocket
from datetime import datetime, timedelta
import json
from collections import defaultdict
from redis.asyncio import Redis

from core.extensions.logger import logger
from core.config.config import settings
from .schemas import WebSocketMessage

class ConnectionManager:
    """
    Менеджер соединений WebSocket\n
    Методы:
        - `register_connection` - Регистрация нового соединения
        - `remove_connection` - Удаление соединения
        - `get_connection` - Получение объекта соединения
        - `get_connection_id` - Получение ID соединения по объекту
        - `check_connections` - Проверка активности соединений
        - `send` - Отправка сообщения в соединение
        - `send_to_user` - Отправка сообщения всем соединениям пользователя
        - `handle_redis_message` - Обработка сообщения из Redis
    """
    def __init__(self, redis: Redis, max_connections_per_user: int, connection_timeout: int):
        self._connections: Dict[str, WebSocket] = {}
        self._user_connections: Dict[int, Set[str]] = defaultdict(set)
        self._connection_users: Dict[str, int] = {}
        self._last_activity: Dict[str, datetime] = {}
        self._redis = redis
        self._metrics = None
        self._max_connections_per_user = max_connections_per_user
        self._connection_timeout = connection_timeout

    def set_metrics(self, metrics) -> None:
        """
        Установка объекта метрик\n
        `metrics` - Объект метрик
        """
        self._metrics = metrics

    async def register_connection(self, connection_id: str, websocket: WebSocket, user_id: Optional[int] = None) -> bool:
        """
        Регистрация нового соединения\n
        `connection_id` - ID соединения\n
        `websocket` - Объект WebSocket соединения\n
        `user_id` - ID пользователя\n
        Возвращает True если регистрация успешна
        """
        if user_id and not await self._check_connection_limit(user_id):
            logger.warning(f"Достигнут лимит соединений для пользователя {user_id}")
            return False

        self._connections[connection_id] = websocket
        self._last_activity[connection_id] = datetime.utcnow()

        if user_id:
            self._user_connections[user_id].add(connection_id)
            self._connection_users[connection_id] = user_id

        if self._metrics:
            self._metrics.increment_connections()

        await self._publish_connection_event("connected", connection_id, user_id)
        logger.info(f"Зарегистрировано соединение {connection_id} для пользователя {user_id}")
        return True

    async def remove_connection(self, connection_id: str) -> None:
        """
        Удаление соединения\n
        `connection_id` - ID соединения
        """
        if connection_id not in self._connections:
            return

        user_id = self._connection_users.get(connection_id)
        if user_id:
            self._user_connections[user_id].discard(connection_id)
            del self._connection_users[connection_id]

        del self._connections[connection_id]
        del self._last_activity[connection_id]

        if self._metrics:
            self._metrics.decrement_connections()

        await self._publish_connection_event("disconnected", connection_id, user_id)
        logger.info(f"Удалено соединение {connection_id}")

    def get_connection(self, connection_id: str) -> Optional[WebSocket]:
        """
        Получение объекта соединения\n
        `connection_id` - ID соединения\n
        Возвращает объект соединения или None
        """
        return self._connections.get(connection_id)

    def get_connection_id(self, websocket: WebSocket) -> Optional[str]:
        """
        Получение ID соединения по объекту\n
        `websocket` - Объект WebSocket соединения\n
        Возвращает ID соединения или None
        """
        for conn_id, conn in self._connections.items():
            if conn == websocket:
                return conn_id
        return None

    async def _check_connection_limit(self, user_id: int) -> bool:
        """
        Проверка лимита соединений для пользователя\n
        `user_id` - ID пользователя\n
        Возвращает True если лимит не превышен
        """
        return len(self._user_connections.get(user_id, set())) < self._max_connections_per_user

    async def send(self, connection_id: str, message: WebSocketMessage) -> bool:
        """
        Отправка сообщения в соединение\n
        `connection_id` - ID соединения\n
        `message` - Сообщение для отправки\n
        Возвращает True если отправка успешна
        """
        websocket = self.get_connection(connection_id)
        if not websocket:
            return False

        try:
            await websocket.send_json(message.dict())
            self._last_activity[connection_id] = datetime.utcnow()
            if self._metrics:
                self._metrics.increment_messages_sent()
            return True
        except Exception as err:
            logger.error(f"Ошибка отправки сообщения в соединение {connection_id}: {err}")
            if self._metrics:
                self._metrics.increment_errors()
            return False

    async def send_to_user(self, user_id: int, message: WebSocketMessage) -> int:
        """
        Отправка сообщения всем соединениям пользователя\n
        `user_id` - ID пользователя\n
        `message` - Сообщение для отправки\n
        Возвращает количество успешно отправленных сообщений
        """
        sent_count = 0
        for connection_id in self._user_connections.get(user_id, set()):
            if await self.send(connection_id, message):
                sent_count += 1
        return sent_count

    async def check_connections(self) -> None:
        """
        Проверка активности соединений
        """
        now = datetime.utcnow()
        timeout = timedelta(seconds=self._connection_timeout)
        
        for connection_id, last_activity in list(self._last_activity.items()):
            if now - last_activity > timeout:
                logger.info(f"Закрытие неактивного соединения {connection_id}")
                await self.remove_connection(connection_id)

    async def _publish_connection_event(self, event_type: str, connection_id: str, user_id: Optional[int] = None) -> None:
        """
        Публикация события соединения в Redis\n
        `event_type` - Тип события\n
        `connection_id` - ID соединения\n
        `user_id` - ID пользователя
        """
        event = {
            "type": event_type,
            "connection_id": connection_id,
            "user_id": user_id
        }
        await self._redis.publish("websocket:connection_events", json.dumps(event))

    async def handle_redis_message(self, message: Dict[str, Any]) -> None:
        """
        Обработка сообщения из Redis\n
        `message` - Сообщение из Redis
        """
        if "connection_id" in message and "message" in message:
            connection_id = message["connection_id"]
            if connection_id in self._connections:
                websocket_message = WebSocketMessage(**message["message"])
                await self.send(connection_id, websocket_message)
