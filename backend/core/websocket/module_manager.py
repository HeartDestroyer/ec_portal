from typing import Dict, List, Optional, Type
from core.extensions.logger import logger
from .schemas import ModuleType

class ModuleManagerRegistry:
    """
    Реестр менеджеров модулей WebSocket\n
    Методы:
        - `register` - Регистрация менеджера модуля
        - `get_manager` - Получение менеджера модуля по типу
        - `get_managers` - Получение всех зарегистрированных менеджеров
        - `set_metrics` - Установка объекта метрик
        - `on_connect` - Обработка нового соединения
        - `on_disconnect` - Обработка отключения
    """
    def __init__(self):
        self._managers: Dict[ModuleType, object] = {}
        self._metrics = None  # Будет установлен извне

    def register(self, module_type: ModuleType, manager: object) -> None:
        """
        Регистрация менеджера модуля\n
        `module_type` - Тип модуля\n
        `manager` - Экземпляр менеджера модуля
        """
        if module_type in self._managers:
            logger.warning(f"Менеджер для модуля {module_type} уже зарегистрирован")
            return

        self._managers[module_type] = manager
        if self._metrics:
            self._metrics.increment_modules()
        logger.info(f"Зарегистрирован менеджер для модуля {module_type}")

    def get_manager(self, module_type: ModuleType) -> Optional[object]:
        """
        Получение менеджера модуля по типу\n
        `module_type` - Тип модуля\n
        Возвращает менеджер модуля или None
        """
        return self._managers.get(module_type)

    def get_managers(self) -> List[object]:
        """
        Получение всех зарегистрированных менеджеров\n
        Возвращает список менеджеров
        """
        return list(self._managers.values())

    def set_metrics(self, metrics) -> None:
        """
        Установка объекта метрик\n
        `metrics` - Объект метрик
        """
        self._metrics = metrics

    async def on_connect(self, connection_id: str, user_id: Optional[int] = None) -> None:
        """
        Обработка нового соединения\n
        `connection_id` - ID соединения\n
        `user_id` - ID пользователя
        """
        for manager in self._managers.values():
            try:
                if hasattr(manager, 'on_connect'):
                    await manager.on_connect(connection_id, user_id)
            except Exception as err:
                logger.error(f"Ошибка при обработке соединения в менеджере {manager.__class__.__name__}: {err}")
                if self._metrics:
                    self._metrics.increment_errors()

    async def on_disconnect(self, connection_id: str, user_id: Optional[int] = None) -> None:
        """
        Обработка отключения\n
        `connection_id` - ID соединения\n
        `user_id` - ID пользователя
        """
        for manager in self._managers.values():
            try:
                if hasattr(manager, 'on_disconnect'):
                    await manager.on_disconnect(connection_id, user_id)
            except Exception as err:
                logger.error(f"Ошибка при обработке отключения в менеджере {manager.__class__.__name__}: {err}")
                if self._metrics:
                    self._metrics.increment_errors() 
