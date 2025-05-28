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

class Group(Base):
    __tablename__ = 'groups'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4, doc="ID группы")
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True, doc="Название группы")
    description: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, doc="Описание группы")
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey('groups.id'), nullable=True, doc="ID родительской группы")

    users: Mapped[List["User"]] = relationship("User", back_populates="group", doc="Список пользователей, относящихся к группе")
    channel_tg_rules: Mapped[List["ChannelRule"]] = relationship("ChannelRule", back_populates="group", doc="Список правил для каналов Telegram")
    parent: Mapped["Group | None"] = relationship("Group", back_populates="children", remote_side=[id], doc="Родительская группа")
    children: Mapped[List["Group"]] = relationship("Group", back_populates="parent", doc="Список дочерних групп")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, doc="Дата создания группы")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, doc="Дата обновления группы")
