from typing import Dict
from datetime import datetime
from core.extensions.logger import logger

class WebSocketMetrics:
    """
    Сборщик метрик WebSocket\n
    Методы:
        - `increment_connections` - Увеличение счетчика соединений
        - `decrement_connections` - Уменьшение счетчика соединений
        - `increment_messages_sent` - Увеличение счетчика отправленных сообщений
        - `increment_messages_received` - Увеличение счетчика полученных сообщений
        - `increment_modules` - Увеличение счетчика зарегистрированных модулей
        - `increment_channels` - Увеличение счетчика активных каналов
        - `decrement_channels` - Уменьшение счетчика активных каналов
        - `increment_errors` - Увеличение счетчика ошибок
        - `get_metrics` - Получение текущих метрик
        - `reset_metrics` - Сброс метрик
    """
    def __init__(self):
        self.metrics: Dict[str, int] = {
            "total_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "modules_registered": 0,
            "channels_active": 0,
            "errors": 0
        }
        self.last_reset = datetime.utcnow()

    def increment_connections(self) -> None:
        """
        Увеличение счетчика соединений
        """
        self.metrics["total_connections"] += 1

    def decrement_connections(self) -> None:
        """
        Уменьшение счетчика соединений
        """
        self.metrics["total_connections"] = max(0, self.metrics["total_connections"] - 1)

    def increment_messages_sent(self) -> None:
        """
        Увеличение счетчика отправленных сообщений
        """
        self.metrics["messages_sent"] += 1

    def increment_messages_received(self) -> None:
        """
        Увеличение счетчика полученных сообщений
        """
        self.metrics["messages_received"] += 1

    def increment_modules(self) -> None:
        """
        Увеличение счетчика зарегистрированных модулей
        """
        self.metrics["modules_registered"] += 1

    def increment_channels(self) -> None:
        """
        Увеличение счетчика активных каналов
        """
        self.metrics["channels_active"] += 1

    def decrement_channels(self) -> None:
        """
        Уменьшение счетчика активных каналов
        """
        self.metrics["channels_active"] = max(0, self.metrics["channels_active"] - 1)

    def increment_errors(self) -> None:
        """
        Увеличение счетчика ошибок
        """
        self.metrics["errors"] += 1

    def get_metrics(self) -> Dict[str, int]:
        """
        Получение текущих метрик\n
        `total_connections` - Общее количество соединений\n
        `messages_sent` - Количество отправленных сообщений\n
        `messages_received` - Количество полученных сообщений\n
        `modules_registered` - Количество зарегистрированных модулей\n
        `channels_active` - Количество активных каналов\n
        `errors` - Количество ошибок
        """
        return self.metrics.copy()

    def reset_metrics(self) -> None:
        """
        Сброс метрик\n
        `total_connections` - Общее количество соединений\n
        `messages_sent` - Количество отправленных сообщений\n
        `messages_received` - Количество полученных сообщений\n
        `modules_registered` - Количество зарегистрированных модулей\n
        `channels_active` - Количество активных каналов\n
        `errors` - Количество ошибок
        """
        self.metrics = {
            "total_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "modules_registered": 0,
            "channels_active": 0,
            "errors": 0
        }
        self.last_reset = datetime.utcnow()
        logger.info("Метрики WebSocket сброшены")
