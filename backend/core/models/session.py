from sqlalchemy import String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from typing import Optional
import uuid
from core.models.base import Base

class Session(Base):
    """
    Модель для хранения информации о сессиях пользователей
    """
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    browser: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    os: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    platform: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Связь с пользователем
    user = relationship("User", back_populates="sessions")

    def to_dict(self):
        """
        Сериализация модели сессии пользователя в словарь
        """
        return {
            "id": self.id,
            "device": self.device,
            "browser": self.browser,
            "ip_address": self.ip_address,
            "os": self.os,
            "platform": self.platform,
            "location": self.location,
            "last_activity": self.last_activity.isoformat(),
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active
        }
