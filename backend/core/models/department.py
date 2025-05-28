import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING, Optional
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from models.base import Base

if TYPE_CHECKING:
    from models.telegram import ChannelRule
    from models.user import User

class Department(Base):
    __tablename__ = 'departments'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4, doc="ID департамента")
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True, doc="Название департамента")
    description: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, doc="Описание департамента")
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey('departments.id'), nullable=True, doc="ID родительского департамента")

    users: Mapped[List["User"]] = relationship("User", back_populates="department", doc="Список пользователей, относящихся к департаменту")
    parent: Mapped["Department | None"] = relationship("Department", back_populates="children", remote_side=[id], doc="Родительский департамент")
    children: Mapped[List["Department"]] = relationship("Department", back_populates="parent", doc="Список дочерних департаментов")
    channel_tg_rules: Mapped[List["ChannelRule"]] = relationship("ChannelRule", back_populates="department", doc="Список правил для каналов Telegram")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, doc="Дата создания департамента")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, doc="Дата обновления департамента")
    