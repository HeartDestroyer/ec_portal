from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from enum import Enum

# Категории уведомлений
class NotificationCategory(str, Enum):
    """
    Категория уведомлений\n
    `login` - Уведомления о входе в систему\n
    `security` - Уведомления о безопасности\n
    `system` - Уведомления о системе\n
    `business` - Уведомления о бизнесе
    """
    LOGIN = "login"
    SECURITY = "security"
    SYSTEM = "system"
    BUSINESS = "business"

# Схема для ключей подписки на push-уведомления
class PushSubscriptionKeys(BaseModel):
    """
    Схема для  Ключи для шифрования push-уведомлений\n
    `p256dh (str)` - Ключ p256dh для шифрования\n
    `auth (str)` - Ключ auth для аутентификации
    """
    p256dh: str = Field(..., description="Ключ p256dh для шифрования")
    auth: str = Field(..., description="Ключ auth для аутентификации")

# Схема для подписки на push-уведомления
class PushSubscriptionInfo(BaseModel):
    """
    Схема для подписки на push-уведомления от браузера\n
    `endpoint (str)` - Endpoint для push-уведомлений\n
    `keys (PushSubscriptionKeys)` - Ключи для push-уведомлений (p256dh, auth)
    """
    endpoint: str = Field(..., description="Endpoint для push-уведомлений")
    keys: PushSubscriptionKeys = Field(..., description="Ключи для push-уведомлений (p256dh, auth)")

# Схема для сохранения подписки
class SubscribeRequest(BaseModel):
    """
    Схема для запроса на подписку пользователя\n
    `user_id (str)` - ID пользователя\n
    `subscription_info (PushSubscriptionInfo)` - Данные подписки от браузера
    """
    user_id: str = Field(..., description="ID пользователя", example="550e8400-e29b-41d4-a716-446655440000")
    subscription_info: PushSubscriptionInfo = Field(..., description="Данные подписки от браузера")

# Схема действий (кнопки) в push-уведомлениях
class NotificationAction(BaseModel):
    """
    Схема для действий (кнопки) в push-уведомлениях\n
    `action (str)` - Действие push-уведомления\n
    `title (str)` - Заголовок действия\n
    `icon (Optional[str])` - Иконка действия
    """
    action: str = Field(..., description="Действие push-уведомления")
    title: str = Field(..., description="Заголовок действия")
    icon: Optional[str] = Field(default=None, description="Иконка действия")

# Схема для отправки одиночного уведомления
class SendNotificationRequest(BaseModel):
    """
    Схема для отправки уведомления одному пользователю\n
    `user_id (str)` - ID пользователя\n
    `title (str)` - Заголовок уведомления\n
    `message (str)` - Текст уведомления\n
    `category (NotificationCategory)` - Категория уведомления\n
    `payload (Optional[Dict[str, Any]])` - Дополнительные данные в JSON\n
    `url (Optional[str])` - URL для перехода при клике
    """
    user_id: str = Field(..., description="ID пользователя", example="550e8400-e29b-41d4-a716-446655440000")
    title: str = Field(..., description="Заголовок уведомления", example="Новое сообщение")
    message: str = Field(..., description="Текст уведомления", example="У вас новое важное сообщение")
    category: NotificationCategory = Field(NotificationCategory.BUSINESS, description="Категория уведомления")
    payload: Optional[Dict[str, Any]] = Field(None, description="Дополнительные данные в JSON", example={"document_id": "123"})
    url: Optional[str] = Field(None, description="URL для перехода при клике", example="/documents/123")

# Схема для массовой отправки
class SendBulkNotificationRequest(BaseModel):
    """
    Схема для массовой отправки уведомлений пользователям\n
    `user_ids (List[str])` - Список ID пользователей\n
    `title (str)` - Заголовок уведомления\n
    `message (str)` - Текст уведомления\n
    `category (NotificationCategory)` - Категория уведомления\n
    `payload (Optional[Dict[str, Any]])` - Дополнительные данные в JSON\n
    `actions (Optional[List[NotificationAction]])` - Действия в уведомлении
    """
    user_ids: List[str] = Field(
        ..., 
        description="Список ID пользователей", 
        example=["550e8400-e29b-41d4-a716-446655440000", "6ba7b810-9dad-11d1-80b4-00c04fd430c8"]
    )
    title: str = Field(..., description="Заголовок уведомления", example="Общее объявление")
    message: str = Field(..., description="Текст уведомления", example="Завтра в 14:00 общее собрание")
    category: NotificationCategory = Field(NotificationCategory.BUSINESS, description="Категория уведомления")
    payload: Optional[Dict[str, Any]] = Field(None, description="Дополнительные данные")
    actions: Optional[List[NotificationAction]] = Field(
        None, 
        description="Действия в уведомлении",
        example=[
            {"action": "view", "title": "Просмотреть"},
            {"action": "dismiss", "title": "Закрыть"}
        ]
    )


# Схема ответа с публичным VAPID ключом
class VapidKeyResponse(BaseModel):
    """
    Схема для ответа с публичным VAPID ключом\n
    `vapid_public_key (str)` - Публичный VAPID ключ
    """
    vapid_public_key: str = Field(..., description="Публичный VAPID ключ")


# Схема статистики отправки уведомлений
class NotificationStats(BaseModel):
    """
    Схема статистики отправки уведомлений
    `total_sent (int)` - Всего отправлено уведомлений
    `total_failed (int)` - Количество неудачных отправок
    `total_no_subscription (int)` - Количество пользователей без подписки
    `active_subscriptions (int)` - Количество активных подписок
    `delivery_rate (float)` - Процент успешной доставки
    """
    total_sent: int = Field(..., description="Всего отправлено уведомлений")
    total_failed: int = Field(..., description="Количество неудачных отправок")
    total_no_subscription: int = Field(..., description="Количество пользователей без подписки")
    active_subscriptions: int = Field(..., description="Количество активных подписок")
    delivery_rate: float = Field(..., description="Процент успешной доставки")

# Схема результата массовой отправки
class BulkNotificationResult(BaseModel):
    """
    Схема результата массовой отправки уведомлений
    `sent (int)` - Количество успешно отправленных
    `failed (int)` - Количество неудачных отправок
    `no_subscription (int)` - Количество пользователей без подписки
    """
    sent: int = Field(..., description="Количество успешно отправленных")
    failed: int = Field(..., description="Количество неудачных отправок") 
    no_subscription: int = Field(..., description="Количество пользователей без подписки")


# Внутренние схемы для работы с данными
class PushSubscription(BaseModel):
    """
    Внутренняя схема подписки для сервиса
    `user_id (str)` - ID пользователя
    `endpoint (str)` - Endpoint для push-уведомлений
    `p256dh (str)` - Ключ p256dh для шифрования
    `auth (str)` - Ключ auth для аутентификации
    `user_agent (Optional[str])` - User Agent браузера
    """
    user_id: str = Field(..., description="ID пользователя")
    endpoint: str = Field(..., description="Endpoint для push-уведомлений")
    p256dh: str = Field(..., description="Ключ p256dh для шифрования")
    auth: str = Field(..., description="Ключ auth для аутентификации")
    user_agent: Optional[str] = Field(default=None, description="User Agent браузера")


# Схема для отправки уведомлений
class NotificationPayload(BaseModel):
    """
    Payload для отправки через WebPush\n
    `title (str)` - Заголовок уведомления\n
    `body (str)` - Текст уведомления\n
    `icon (Optional[str])` - Иконка уведомления\n
    `badge (Optional[str])` - Иконка для счетчика уведомлений\n
    `tag (Optional[str])` - Тег уведомления\n
    `data (Optional[Dict[str, Any]])` - Дополнительные данные в JSON\n
    `actions (Optional[List[NotificationAction]])` - Действия в уведомлении\n
    `requireInteraction (bool)` - Требуется ли взаимодействие с уведомлением
    """
    title: str = Field(..., description="Заголовок уведомления")
    body: str = Field(..., description="Текст уведомления")
    icon: Optional[str] = Field(default=None, description="Иконка уведомления")
    badge: Optional[str] = Field(default=None, description="Иконка для счетчика уведомлений")
    tag: Optional[str] = Field(default=None, description="Тег уведомления")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Дополнительные данные в JSON")
    actions: Optional[List[NotificationAction]] = Field(default=None, description="Действия в уведомлении")
    requireInteraction: bool = Field(default=False, description="Требуется ли взаимодействие с уведомлением")
