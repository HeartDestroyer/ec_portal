# backend/core/models/group.py

from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from core.models.base import Base
from typing import List, TYPE_CHECKING
import uuid
from sqlalchemy.dialects.postgresql import UUID


# Предотвращение циклического импорта для type hinting
if TYPE_CHECKING:
    from .user import User # noqa

# Модель группы
class Group(Base):
    """
    Модель Группы (или отдела внутри департамента)
    """
    __tablename__ = 'groups'

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String(256), unique=True, nullable=False, index=True, doc="Название группы")
    description = Column(String(512), nullable=True, doc="Описание группы")
    parent_id = Column(UUID(as_uuid=True), ForeignKey('groups.id'), nullable=True, doc="ID родительской группы")

    users: List["User"] = relationship("User", back_populates="group")
    parent = relationship("Group", back_populates="children")
    children = relationship("Group", back_populates="parent")

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
