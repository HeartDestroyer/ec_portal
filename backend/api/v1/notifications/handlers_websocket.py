from typing import Optional

from core.websocket.schemas import WebSocketMessage, MessageHandler, ConnectionInfo, ModuleType

class NotificationMessageHandler(MessageHandler):
    """
    Обработчик сообщений уведомлений\n
    Методы:
        - `handle_message` - Обработка сообщений
    """
    
    async def handle_message(self, message: WebSocketMessage, connection_info: ConnectionInfo) -> Optional[WebSocketMessage]:
        """
        Обработка сообщений\n
        `message` - Сообщение\n
        `connection_info` - Информация о подключении\n
        Возвращает None, если сообщение не обработано
        """
        if message.type == "notification_read":
            # Отмечаем уведомление прочитанным
            notification_id = message.data.get("notification_id")
            await self._mark_notification_read(notification_id, connection_info.user_id)
            
            return WebSocketMessage(
                type="notification_read_confirmed",
                module=ModuleType.NOTIFICATIONS,
                data={"notification_id": notification_id}
            )
        
        return None
