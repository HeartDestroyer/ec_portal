from sqlalchemy import String, Text, DateTime, Integer, JSON, Boolean, Enum
from sqlalchemy.sql import func
from models.base import Base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
import uuid
from datetime import datetime
from typing import Optional
import enum

# Статусы уведомлений
class NotificationStatus(enum.Enum):
    """
    Статусы уведомлений
    """
    SENT = "sent"
    FAILED = "failed"
    NO_SUBSCRIPTION = "no_subscription"
    READ = "read"

# Подписка на push-уведомления
class PushSubscription(Base):
    """
    Подписка на push-уведомления
    """
    __tablename__ = "webpush_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True, comment="ID пользователя")
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, index=True, comment="Endpoint для push-уведомлений")
    p256dh_key: Mapped[str] = mapped_column(Text, nullable=False, comment="Ключ p256dh для шифрования")
    auth_key: Mapped[str] = mapped_column(Text, nullable=False, comment="Ключ auth для аутентификации")
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="User Agent браузера")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="Активна ли подписка")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, comment="Дата создания")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=func.now(), comment="Дата обновления")

# Логи push-уведомлений
class NotificationLog(Base):
    """
    Логи push-уведомлений
    """
    __tablename__ = "webpush_notification_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True, comment="ID пользователя")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="Заголовок уведомления")
    message: Mapped[str] = mapped_column(Text, nullable=False, comment="Текст уведомления")
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True, comment="Категория уведомления")
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="Дополнительные данные")
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Ссылка для перехода")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True, comment="Прочитано")
    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), nullable=False, default=NotificationStatus.SENT, comment="Статус отправки")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Сообщение об ошибке")
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True, comment="Дата отправки")

# Статистика push-уведомлений
class NotificationStats(Base):
    """
    Статистика push-уведомлений
    """
    __tablename__ = "webpush_notification_stats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True, comment="Дата статистики")
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True, comment="Категория уведомлений")
    total_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Всего отправлено")
    total_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Всего ошибок")
    total_no_subscription: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Без подписки")
    total_read: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Прочитано")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True, comment="Дата создания")
