from typing import Optional, List, Dict, Any
import json
from pywebpush import webpush, WebPushException
from fastapi import HTTPException, status
from sqlalchemy import select, or_, update
from datetime import datetime
from redis.asyncio import Redis
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from core.security.session import JsonCoder
from fastapi_cache import FastAPICache
import asyncio

from .schemas import PushSubscriptionInfo, SendNotificationRequest, SendBulkNotificationRequest, VapidKeyResponse, NotificationStats, BulkNotificationResult, NotificationPayload
from models.notifications import PushSubscription, NotificationLog, NotificationStats
from api.v1.dependencies import settings, logger
from api.v1.schemas import MessageResponse


class CustomJsonCoder(JsonCoder):
    """
    JsonCoder, который:
      - При записи в Redis отдаёт plain JSON-строку (str), так что с decode_responses=True всё ровно сохраняется/читается как str
      - При загрузке принимает и bytes, и str и всегда возвращает Python-объект
    """    
    def dump(self, value: any) -> any:
        return json.dumps(value, default=self.default)

    def load(self, value: any) -> any:
        text = value.decode("utf-8") if isinstance(value, (bytes, bytearray)) else value
        return json.loads(text)
    

class NotificationService:
    """
    Сервис для управления push-уведомлениями
    Методы:
        - `get_subscription` - Получение подписки пользователя по endpoint
        - `get_subscriptions` - Получение всех подписок пользователя по ID пользователя
        - `send_push_notification` - Отправка push-уведомления пользователю
        - `log_notification` - Сохранение статистики уведомлений
        - `save_subscription` - Сохранение подписки пользователя или обновление существующей
        - `delete_subscription` - Удаление подписки пользователя
        - `get_vapid_public_key` - Получение публичного VAPID ключа
        - `send_notification` - Основной метод отправки уведомления пользователю на все подписки
        - `send_bulk_notifications` - Массовая отправка уведомлений
        - `get_notification_stats` - Получение статистики по уведомлениям
        - `get_notification_history` - Получение истории уведомлений пользователя
        - `read_notification` - Отметка уведомления как прочитанного
        - `read_all_notifications` - Отметка всех уведомлений пользователя как прочитанных

        TODO:\n
            - Добавить интеграцию с RabbitMQ вместо прямого await send_push_notification(...) публикуем событие, а воркер подписывается на канал и обрабатывает отправку
            - Добавить фоновые задачи: Celery для работы с RabbitMQ
    """

    def __init__(self, db: AsyncSession, redis: Redis, jwt_handler=None, email_manager=None):
        self.db = db
        self.redis = redis
        self.jwt_handler = jwt_handler
        self.email_manager = email_manager
        self.vapid_private_key = settings.VAPID_PRIVATE_KEY
        self.vapid_public_key = settings.VAPID_PUBLIC_KEY
        self.vapid_claims = {
            "sub": f"mailto:{settings.VAPID_EMAIL}"
        }

    @cache(expire=3600, coder=CustomJsonCoder, namespace="webpush:subscription:endpoint")
    async def get_subscription(self, endpoint: str) -> Optional[PushSubscription]:
        """
        Получение подписки пользователя\n
        `endpoint` - Эндпоинт подписки\n
        Возвращает PushSubscription - Подписка пользователя, None - Не удалось получить подписку
        """
        try:
            query = await self.db.execute(
                select(PushSubscription).where(
                    PushSubscription.endpoint == endpoint
                )
            )
            subscription = query.scalar_one_or_none()
            return subscription
        
        except Exception as err:
            logger.error(f"Ошибка при получении подписки: {err}")
            return None

    @cache(expire=3600, coder=CustomJsonCoder, namespace="webpush:subscriptions:user_id")
    async def get_subscriptions(self, user_id: str) -> List[PushSubscription]:
        """
        Получение всех подписок пользователя по ID пользователя\n
        `user_id` - ID пользователя\n
        Возвращает список PushSubscription - Подписки пользователя или пустой список
        """
        try:
            query = await self.db.execute(
                select(PushSubscription).where(
                    PushSubscription.user_id == user_id
                )
            )
            subscriptions = query.scalars().all()
            return [PushSubscription.model_validate(s) for s in subscriptions]

        except Exception as err:
            logger.error(f"Ошибка при получении подписок: {err}")
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        reraise=True
    )
    async def _webpush(self, subscription_info: dict, payload: NotificationPayload, user_id: str, endpoint: str) -> None:
        """
        Отправка push-уведомления\n
        `subscription_info` - Информация о подписке\n
        `payload` - Данные уведомления\n
        `user_id` - ID пользователя\n
        `endpoint` - Эндпоинт подписки\n
        """
        try:
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(payload.model_dump()),
                vapid_private_key=self.vapid_private_key,
                vapid_claims=self.vapid_claims
            )
        except WebPushException as err:
            logger.error(f"Ошибка при отправке push-уведомления пользователю {user_id} на подписку {endpoint}: {err}")
            # Если подписка истекла или недействительна, удаляем её
            if getattr(err, "response", None) and err.response.status_code == 410:
                await self.delete_subscription(endpoint)
                return
            raise

    async def send_push_notification(self, subscription: PushSubscription, notification: SendNotificationRequest) -> bool:
        """
        Отправка push-уведомления\n
        `subscription` - Подписка пользователя в виде PushSubscription\n
        `notification` - Уведомление в виде SendNotificationRequest\n
        Возвращает True - Уведомление отправлено успешно, False - Не удалось отправить уведомление
        """
        try:
            payload = NotificationPayload(
                title=notification.title,
                body=notification.message,
                data={
                    "category": notification.category,
                    "payload": notification.payload
                }
            )

            # Формируем информацию о подписке
            subscription_info = {
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh_key,
                    "auth": subscription.auth_key
                }
            }

            # Отправляем push-уведомление
            await self._webpush(subscription_info, payload, subscription.user_id, subscription.endpoint)
            return True
        
        except RetryError as err:
            logger.error(f"Сервер веб-пушей недоступен, переход в режим деградации: {err}")
            return False
        except Exception as err:
            logger.error(f"Ошибка при отправке push-уведомления пользователю {subscription.user_id} на подписку {subscription.endpoint}: {err}")
            return False

    async def log_notification(self, user_id: str, title: str, message: str, category: Optional[str], payload: Optional[dict], url: Optional[str], status: str = "sent", error_message: Optional[str] = None) -> None:
        """
        Сохранение статистики уведомлений\n
        `user_id` - ID пользователя\n
        `title` - Заголовок уведомления\n
        `message` - Сообщение уведомления\n
        `category` - Категория уведомления\n
        `payload` - Дополнительные данные\n
        `url` - URL-адрес, в уведомлении\n
        `status` - Статус отправки (sent, failed, error, no_subscription)\n
        `error_message` - Сообщение об ошибке\n
        """
        try:
            new_notification_log = NotificationLog(
                user_id=user_id,
                title=title,
                message=message,
                category=category,
                payload=payload,
                url=url,
                status=status,
                error_message=error_message
            )
            self.db.add(new_notification_log)
            await self.db.commit()

        except Exception as err:
            logger.error(f"Ошибка при сохранении статистики уведомлений пользователя {user_id}: {err}")
            await self.db.rollback()

    # Сохранение подписки и удаление
    async def save_subscription(self, user_id: str, subscription: PushSubscriptionInfo) -> bool:
        """
        Сохранение подписки пользователя\n
        `user_id` - ID пользователя\n
        `subscription` - Подписка пользователя в виде PushSubscriptionInfo\n
        Возвращает True - Подписка успешно сохранена, False - Не удалось сохранить подписку
        """
        try:
            subscription_obj = await self.get_subscription(subscription.endpoint)
            if subscription_obj:
                subscription_obj.user_id = user_id
                subscription_obj.p256dh_key = subscription.keys.p256dh
                subscription_obj.auth_key = subscription.keys.auth
                subscription_obj.user_agent = subscription.user_agent
                subscription_obj.is_active = True
            else:
                new_subscription = PushSubscription(
                    user_id=user_id,
                    endpoint=subscription.endpoint,
                    p256dh_key=subscription.keys.p256dh,
                    auth_key=subscription.keys.auth,
                    user_agent=subscription.user_agent,
                )
                self.db.add(new_subscription)

            await self.db.commit()
            await FastAPICache.clear(f"webpush")
            return True
        
        except Exception as err:
            logger.error(f"Ошибка при сохранении подписки пользователя {user_id}: {err}")
            await self.db.rollback()
            return False

    async def delete_subscription(self, endpoint: str) -> bool:
        """
        Удаление подписки пользователя\n
        `endpoint` - Эндпоинт подписки\n
        Возвращает True - Подписка удалена успешно, False - Не удалось удалить подписку
        """
        try:
            subscription = await self.get_subscription(endpoint)
            if subscription:
                subscription.is_active = False
                await self.db.commit()
                await FastAPICache.clear(f"webpush")
                return True
            else:
                return False

        except Exception as err:
            logger.error(f"Ошибка при удалении подписки: {err}")
            await self.db.rollback()
            return False


    # Получение VAPID ключа
    def get_vapid_public_key(self) -> str:
        """
        Получение публичного VAPID ключа\n
        Возвращает строку - Публичный VAPID ключ
        """
        return self.vapid_public_key 

    # Отправка уведомлений с использованием asyncio.gather
    async def send_notification(self, notification: SendNotificationRequest) -> bool:
        """
        Основной метод отправки уведомления пользователю на все подписки с использованием asyncio.gather\n
        `notification` - Уведомление в виде SendNotificationRequest\n
        Возвращает True - Уведомление отправлено успешно, False - Не удалось отправить уведомление
        """
        try:
            subscriptions = await self.get_subscriptions(notification.user_id)
            if subscriptions:
                results = await asyncio.gather(
                    *(self.send_push_notification(s, notification) for s in subscriptions),
                    return_exceptions=True
                )
                for result in results:
                    if result:
                        await self.log_notification(notification.user_id, notification.title, notification.message, notification.category, notification.payload, notification.url, "sent")
                        logger.info(f"Push-уведомление отправлено пользователю {notification.user_id}: {notification.title}")
                    else:
                        await self.log_notification(notification.user_id, notification.title, notification.message, notification.category, notification.payload, notification.url, "failed")
            else:
                await self.log_notification(notification.user_id, notification.title, notification.message, notification.category, notification.payload, notification.url, "no_subscription")
            return True
            
        except Exception as err:
            logger.error(f"Ошибка при отправке уведомления пользователю {notification.user_id}: {err}")
            await self.log_notification(notification.user_id, notification.title, notification.message, notification.category, notification.payload, notification.url, "error")
            return False

    async def send_bulk_notifications(self, bulk_request: SendBulkNotificationRequest) -> None:
        """
        Массовая отправка уведомлений\n
        `bulk_request` - Массовая отправка уведомлений в виде SendBulkNotificationRequest\n
        """
        for user_id in bulk_request.user_ids:
            try:
                await self.send_notification(
                    notification=SendNotificationRequest(
                        user_id=user_id,
                        title=bulk_request.title,
                        message=bulk_request.message,
                        category=bulk_request.category,
                        payload=bulk_request.payload,
                        actions=bulk_request.actions
                    )
                )
                
            except Exception as err:
                logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {err}")
                await self.log_notification(user_id, bulk_request.title, bulk_request.message, bulk_request.category, bulk_request.payload, bulk_request.url, "error")
        
        logger.info(f"Массовая отправка уведомлений завершена")

    # Статистика
    async def get_notification_stats(self) -> NotificationStats:
        """
        Получение статистики по уведомлениям\n
        Возвращает статистику по уведомлениям в виде NotificationStats
        """
        try:
            stats = await self.db.execute(select(NotificationStats))
            return stats.scalar_one_or_none()
        except Exception as err:
            logger.error(f"Ошибка при получении статистики по уведомлениям: {err}")
            return None


    # Notification Center
    async def get_notification_history(self, user_id: str, limit: int = 100, offset: int = 0) -> list[NotificationLog]:
        """
        Получение истории уведомлений пользователя\n
        `user_id` - ID пользователя\n
        `limit` - Количество записей на страницу\n
        `offset` - Смещение\n
        Возвращает список NotificationLog - История уведомлений пользователя
        """
        try:
            result = await self.db.execute(
                select(NotificationLog)
                .where(NotificationLog.user_id == user_id)
                .order_by(NotificationLog.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return result.scalars().all()
        
        except Exception as err:
            logger.error(f"Ошибка при получении истории уведомлений пользователя {user_id}: {err}")
            return []

    async def read_notification(self, notification_id: str) -> None:
        """
        Отметка уведомления как прочитанного\n
        `notification_id` - ID уведомления\n
        """
        try:
            await self.db.execute(
                update(NotificationLog)
                    .where(NotificationLog.id == notification_id)
                    .values(is_read=True))
            await self.db.commit()
        except Exception as err:
            logger.error(f"Ошибка при отметке уведомления как прочитанного {notification_id}: {err}")
            await self.db.rollback()

    async def read_all_notifications(self, user_id: str) -> None:
        """
        Отметка всех уведомлений пользователя как прочитанных\n
        `user_id` - ID пользователя\n
        """
        try:
            await self.db.execute(
                update(NotificationLog)
                    .where(
                        NotificationLog.user_id == user_id, 
                        NotificationLog.is_read == False)
                    .values(is_read=True))
            await self.db.commit()
        except Exception as err:
            logger.error(f"Ошибка при отметке всех уведомлений пользователя {user_id} как прочитанных: {err}")
            await self.db.rollback()
