# backend/core/models/department.py

import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING, Optional
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from core.models.base import Base

if TYPE_CHECKING:
    from .user import User

# Модель департамента
class Department(Base):
    """
    Модель Департамента
    """
    __tablename__ = 'departments'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True, doc="Название департамента")
    description: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, doc="Описание департамента")
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey('departments.id'), nullable=True, doc="ID родительского департамента")

    # Связи
    users: Mapped[List["User"]] = relationship("User", back_populates="department")
    parent: Mapped["Department | None"] = relationship("Department", back_populates="children", remote_side=[id])
    children: Mapped[List["Department"]] = relationship("Department", back_populates="parent")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Сериализация модели департамента в словарь
    def to_dict(self):
        """
        Сериализация модели департамента в словарь
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "parent_id": str(self.parent_id) if self.parent_id else None
        }
    
    # Сериализация модели департамента в словарь с публичными данными
    def to_public_dict(self):
        """
        Сериализация модели департамента в словарь с публичными данными
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description
        }
