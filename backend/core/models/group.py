# backend/core/models/group.py

import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from core.models.base import Base

if TYPE_CHECKING:
    from .user import User

# Модель группы
class Group(Base):
    """
    Модель Группы (или отдела внутри департамента)
    """
    __tablename__ = 'groups'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True, doc="Название группы")
    description: Mapped[str | None] = mapped_column(String(512), nullable=True, doc="Описание группы")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('groups.id'), nullable=True, doc="ID родительской группы")

    # Связи
    users: Mapped[List["User"]] = relationship("User", back_populates="group")
    parent: Mapped["Group | None"] = relationship("Group", back_populates="children", remote_side=[id])
    children: Mapped[List["Group"]] = relationship("Group", back_populates="parent")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Сериализация модели группы в словарь
    def to_dict(self):
        """
        Сериализация модели группы в словарь
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "parent_id": str(self.parent_id) if self.parent_id else None
        }
    
    # Сериализация модели группы в словарь с публичными данными
    def to_public_dict(self):
        """
        Сериализация модели группы в словарь с публичными данными
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description
        }
