from typing import Dict, List, Optional, Callable, Any, Awaitable
from collections import defaultdict

from core.extensions.logger import logger
from .schemas import MessageType, ModuleType, WebSocketMessage

class MessageHandlerManager:
    """
    Менеджер обработчиков сообщений WebSocket\n
    Методы:
        - `register` - Регистрация обработчика сообщений
        - `set_metrics` - Установка объекта метрик
        - `handle` - Обработка входящего сообщения
        - `get_handlers` - Получение обработчиков для конкретного типа сообщения и модуля
    """
    def __init__(self):
        self._handlers: Dict[MessageType, Dict[ModuleType, List[Callable[[WebSocketMessage], Awaitable[None]]]]] = defaultdict(lambda: defaultdict(list))
        self._metrics = None  # Будет установлен извне

    def register(self, message_type: MessageType, module_type: ModuleType, handler: Callable[[WebSocketMessage], Awaitable[None]]) -> None:
        """
        Регистрация обработчика сообщений\n
        `message_type` - Тип сообщения\n
        `module_type` - Тип модуля\n
        `handler` - Функция-обработчик
        """
        self._handlers[message_type][module_type].append(handler)
        logger.info(f"Зарегистрирован обработчик для {message_type} в модуле {module_type}")

    def set_metrics(self, metrics) -> None:
        """
        Установка объекта метрик\n
        `metrics` - Объект метрик
        """
        self._metrics = metrics

    async def handle(self, message: WebSocketMessage) -> None:
        """
        Обработка входящего сообщения\n
        `message` - Входящее сообщение
        """
        if self._metrics:
            self._metrics.increment_messages_received()

        handlers = self._handlers.get(message.type, {}).get(message.module, [])
        if not handlers:
            logger.warning(f"Нет обработчиков для сообщения типа {message.type} в модуле {message.module}")
            return

        for handler in handlers:
            try:
                await handler(message)
            except Exception as err:
                logger.error(f"Ошибка при обработке сообщения {message.type} в модуле {message.module}: {err}")
                if self._metrics:
                    self._metrics.increment_errors()

    def get_handlers(self, message_type: MessageType, module_type: ModuleType) -> List[Callable[[WebSocketMessage], Awaitable[None]]]:
        """
        Получение обработчиков для конкретного типа сообщения и модуля\n
        `message_type` - Тип сообщения\n
        `module_type` - Тип модуля\n
        Возвращает список обработчиков
        """
        return self._handlers.get(message_type, {}).get(module_type, [])
