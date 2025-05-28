from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import Optional

from .schemas import SubscribeRequest, SendNotificationRequest, SendBulkNotificationRequest, VapidKeyResponse, NotificationStats, BulkNotificationResult, NotificationPayload
from api.v1.schemas import MessageResponse, TokenPayload
from api.v1.dependencies import (
    JWTHandler, EmailManager,
    get_db, get_redis, settings, logger, jwt_handler, email_manager,
    require_admin_roles, require_authenticated, get_current_user_payload, get_current_active_user,
)
from api.v1.notifications.service import NotificationService

notifications_router = APIRouter(prefix="/api/v1/notifications", tags=["Управление уведомлениями"])

def create_notification_service(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    jwt_handler: Optional[JWTHandler] = Depends(JWTHandler),
    email_manager: Optional[EmailManager] = Depends(EmailManager),
) -> NotificationService:
    """
    Создает экземпляр сервиса уведомлений
    """
    return NotificationService(db, redis, jwt_handler, email_manager)


# Подписка на push-уведомления
@notifications_router.post(
    "/subscribe",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Подписка на push-уведомления"
)
@require_authenticated()
async def subscribe_push(
    request: Request,
    subscription: SubscribeRequest,
    notification_service: NotificationService = Depends(create_notification_service)
) -> MessageResponse:
    """
    Авторизованный API. Доступ: `Авторизованные пользователи`\n
    Подписывает пользователя на push-уведомления\n
    `subscription` - Подписка на push-уведомления в формате `SubscribeRequest`
    """
    subscription_saved = await notification_service.save_subscription(subscription.user_id, subscription.subscription_info)
    if subscription_saved:
        return MessageResponse(message="Подписка на push-уведомления успешно сохранена")
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Не удалось сохранить подписку на push-уведомления")

# Отписка от push-уведомлений
@notifications_router.delete(
    "/unsubscribe/{endpoint}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Отписка от уведомлений"
)
@require_authenticated()
async def unsubscribe_push(
    endpoint: str,
    notification_service: NotificationService = Depends(create_notification_service),
    token_payload: TokenPayload = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Авторизованный API. Доступ: `Авторизованные пользователи`, `Администраторы`\n
    Отписывает пользователя от push-уведомлений\n
    `endpoint` - Эндпоинт подписки
    """
    user = await get_current_active_user(token_payload, db)
    if user.role not in settings.ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа")

    deleted = await notification_service.delete_subscription(endpoint)
    if deleted:
        return MessageResponse(message="Подписка на push-уведомления успешно удалена")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Подписка на push-уведомления не найдена")


# Получение публичного VAPID ключа для подписки на push-уведомления
@notifications_router.get(
    "/vapidkey",
    response_model=VapidKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение публичного ключа VAPID"
)
@require_authenticated()
async def get_vapid_public_key(
    request: Request,
    notification_service: NotificationService = Depends(create_notification_service)
) -> VapidKeyResponse:
    """
    Авторизованный API. Доступ: `Авторизованные пользователи`\n
    Получение публичного VAPID ключа для подписки на push-уведомления\n
    Этот ключ используется браузером для создания подписки на push-уведомления
    """
    try:
        vapid_key = notification_service.get_vapid_public_key()
        return VapidKeyResponse(vapid_public_key=vapid_key)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка получения VAPID ключа")


# Отправка уведомления пользователю
@notifications_router.post(
    "/send",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Отправка уведомления пользователю"
)
@require_admin_roles()
async def send_notification(
    request: Request,
    notification: SendNotificationRequest,
    notification_service: NotificationService = Depends(create_notification_service)
) -> MessageResponse:
    """
    Административный API. Доступ: `Администраторы`\n
    Отправка push-уведомления пользователю\n
    `notification` - Уведомление в формате `SendNotificationRequest`
    """
    success = await notification_service.send_notification(notification)
    if success:
        return MessageResponse(message="Уведомление отправлено")
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Не удалось отправить уведомление")

# Массовая отправка уведомлений
@notifications_router.post(
    "/sendbulk",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Массовая отправка уведомлений"
)
@require_admin_roles()
async def send_bulk_notifications(
    request: Request,
    bulk_request: SendBulkNotificationRequest,
    notification_service: NotificationService = Depends(create_notification_service)
) -> MessageResponse:
    """
    Административный API. Доступ: `Администраторы`\n
    Массовая отправка push-уведомлений списку пользователей\n
    `bulk_request` - Массовая отправка уведомлений в формате `SendBulkNotificationRequest`
    """
    await notification_service.send_bulk_notifications(bulk_request)
    return MessageResponse(message="Уведомления отправлены")

# Получение статистики по уведомлениям
@notifications_router.get(
    "/statistics",
    response_model=NotificationStats,
    status_code=status.HTTP_200_OK,
    summary="Статистика уведомлений"
)
@require_admin_roles()
async def get_notification_stats(
    request: Request,
    notification_service: NotificationService = Depends(create_notification_service)
) -> NotificationStats:
    """
    Административный API. Доступ: `Администраторы`\n
    Получение статистики по уведомлениям
    """
    return await notification_service.get_notification_stats()


# История уведомлений пользователя в Notification Center
@notifications_router.get(
    "/history/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="История отправки уведомлений в Notification Center"
)
@require_authenticated()
async def get_notification_history(
    request: Request,
    user_id: str,
    token_payload: TokenPayload = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
    notification_service: NotificationService = Depends(create_notification_service),
    limit: int = 50,
    offset: int = 0
) -> MessageResponse:
    """
    Авторизованный API. Доступ: `Авторизованные пользователи`, `Администраторы`\n
    История отправки уведомлений пользователя в Notification Center\n
    `user_id` - ID пользователя\n
    `limit` - Количество записей на страницу\n
    `offset` - Смещение
    """
    user = await get_current_active_user(token_payload, db)
    if str(user.id) != user_id and user.role not in settings.ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа")

    history = await notification_service.get_notification_history(user_id, limit, offset)
    history_data = [log.model_dump() for log in history]
    return MessageResponse(message="История отправки уведомлений получена", data=history_data)

# Отметить уведомление как прочитанное в Notification Center
@notifications_router.post(
    "/read/{notification_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Отметить уведомление как прочитанное в Notification Center"
)
@require_authenticated()
async def read_notification(
    request: Request,
    notification_id: str,
    notification_service: NotificationService = Depends(create_notification_service)
) -> MessageResponse:
    """
    Авторизованный API. Доступ: `Авторизованные пользователи`\n
    Отметить уведомление как прочитанное в Notification Center\n
    `notification_id` - ID уведомления
    """
    await notification_service.read_notification(notification_id)
    return MessageResponse(message="Уведомление отмечено как прочитанное")

# Отметить все уведомления как прочитанные в Notification Center
@notifications_router.post(
    "/allread/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Отметить все уведомления как прочитанные в Notification Center"
)
@require_authenticated()
async def read_all_notifications(
    request: Request,
    user_id: str,
    notification_service: NotificationService = Depends(create_notification_service)
) -> MessageResponse:
    """
    Авторизованный API. Доступ: `Авторизованные пользователи`\n
    Отметить все уведомления как прочитанные в Notification Center\n
    `user_id` - ID пользователя
    """
    await notification_service.read_all_notifications(user_id)
    return MessageResponse(message="Все уведомления отмечены как прочитанные")
