# backend/core/models/department.py

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from core.models.base import Base
from typing import List, TYPE_CHECKING
import uuid
from sqlalchemy.dialects.postgresql import UUID


# Предотвращение циклического импорта для type hinting
if TYPE_CHECKING:
    from .user import User

# Модель департамента
class Department(Base):
    """
    Модель Департамента
    """
    __tablename__ = 'departments'

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String(128), nullable=False, unique=True, doc="Название департамента")
    description = Column(String(512), nullable=True, doc="Описание департамента")
    parent_id = Column(UUID(as_uuid=True), ForeignKey('departments.id'), nullable=True, doc="ID родительского департамента")

    # Связи
    users: List["User"] = relationship("User", back_populates="department")
    parent = relationship("Department", back_populates="children")
    children = relationship("Department", back_populates="parent")
    
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
