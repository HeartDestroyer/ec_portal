from sqlalchemy import String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from typing import Optional
import uuid
from models.base import Base

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4, doc="ID сессии")
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, doc="ID пользователя")
    device: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, doc="Устройство")
    browser: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, doc="Браузер устройства  ")
    ip_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, doc="IP-адрес устройства")
    os: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, doc="Операционная система устройства")
    platform: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, doc="Платформа устройства")
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, doc="Местоположение устройства")
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, doc="Последняя активность сессии")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, doc="Дата создания сессии")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, doc="Активность сессии")

    user = relationship("User", back_populates="sessions")
