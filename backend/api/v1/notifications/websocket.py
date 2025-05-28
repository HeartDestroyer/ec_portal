from typing import List
from core.websocket.schemas import ModuleType, Channel, ModuleManager, ConnectionInfo
from .service import NotificationService

class NotificationModuleManager(ModuleManager):
    """
    Менеджер модуля уведомлений\n
    Методы:
        - `on_connect` - Вызывается при подключении пользователя
        - `on_disconnect` - Вызывается при отключении пользователя
        - `get_user_channels` - Получение каналов пользователя для модуля
    """
    module_type = ModuleType.NOTIFICATIONS

    def __init__(self, notification_service: NotificationService):
        self.service = notification_service

    async def on_connect(self, connection_info: ConnectionInfo) -> None:
        """
        Уведомления при подключении\n
        `connection_info` - Информация о подключении\n
        Можно отправить кол-во непрочитанных уведомлений
        """
        pass
    
    async def on_disconnect(self, connection_info: ConnectionInfo) -> None:
        """
        Действия при отключении\n
        `connection_info` - Информация о подключении\n
        Можно удалить все уведомления пользователя
        """
        pass

    async def get_user_channels(self, user_id: str) -> List[Channel]:
        """
        Каналы уведомлений для пользователя\n
        `user_id` - ID пользователя\n
        Возвращает список каналов для пользователя
        """

        return [
            Channel(
                module=ModuleType.NOTIFICATIONS,
                name=f"user_{user_id}",
                permissions=["notifications.read"],
                metadata={"user_id": user_id}
            ),
            Channel(
                module=ModuleType.NOTIFICATIONS,
                name="global",
                permissions=["notifications.read"]
            )
        ]
