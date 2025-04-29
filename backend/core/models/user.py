# backend/core/models/user.py

import enum
import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Date, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from core.models.base import Base
from core.models.department import Department
from core.models.group import Group

# Роли пользователей
class Role(enum.Enum):
    SUPER_ADMIN = "superadmin"
    ADMIN = "admin"
    LEADER = "leader"
    EMPLOYEE = "employee"
    GUEST = "guest"

# Дополнительные роли
class AdditionalRole(enum.Enum):
    COORDINATOR_OTS = "coordinator_ots"
    COORDINATOR_OP = "coordinator_op"

# Пол
class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"

# Компании
class Company(enum.Enum):
    ITSK = 'ООО "ИТСК"'
    EC_TECHNOLOGIES = 'ООО "ЭЦ-Технологии"'
    EXPERT_CENTER_FINANCE = 'ООО УК "ЭкспертЦентрФинанс"'
    EXPERT_CENTER_SAMARA = 'ООО "Эксперт Центр Самара"'
    NEC = 'ООО "НЭЦ"'
    EEC = 'ООО "ЕЭЦ"'
    ECSP = 'ООО "ЭЦСП"'
    ENN = 'ООО "ЭНН"'

# Города
class City(enum.Enum):
    UFA = 'Уфа'
    MOSCOW = 'Москва'
    SPB = 'Санкт-Петербург'
    SAMARA = 'Самара'
    KRASNODAR = 'Краснодар'
    EKATERINBURG = 'Екатеринбург'
    NIZHNY_NOVGOROD = 'Нижний Новгород'
    KRASNOYARSK = 'Красноярск'
    NOVOSIBIRSK = 'Новосибирск'
    STERLITAMAK = 'Стерлитамак'

# Пользователи
class User(Base):
    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    login: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(256), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(25), nullable=True, default=None, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey('departments.id'), nullable=True, doc="ID департамента")
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey('groups.id'), nullable=True, doc="ID группы")

    work_position: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, doc="Должность")
    date_employment: Mapped[Optional[date]] = mapped_column(Date, nullable=True, doc="Дата трудоустройства")
    city: Mapped[Optional[City]] = mapped_column(Enum(City), nullable=True, index=True, doc="Город")
    date_birthday: Mapped[Optional[date]] = mapped_column(Date, nullable=True, doc="Дата рождения")
    company: Mapped[Optional[Company]] = mapped_column(Enum(Company), nullable=True, index=True, doc="Компания")
    bitrix_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True, doc="ID в Битриксе")
    qr_code_vcard: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, doc="QR-код vCard")
    user_email: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, doc="Рабочая почта")
    telegram_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True, doc="Телеграм ID")
    gender: Mapped[Optional[Gender]] = mapped_column(Enum(Gender), nullable=True, index=True, doc="Пол")
    photo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, doc="URL фотографии пользователя")
    photo_url_small: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, doc="URL уменьшенной фотографии пользователя")
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True, doc="Биография или описание пользователя")

    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.GUEST, nullable=False, index=True, doc="Роль")
    additional_role: Mapped[Optional[AdditionalRole]] = mapped_column(Enum(AdditionalRole), nullable=True, index=True, doc="Дополнительная роль")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
    failed_login_attempts: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_password_change: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, doc="Дата последнего изменения пароля")

    # Связи
    department: Mapped[Optional["Department"]] = relationship("Department", back_populates="users")
    group: Mapped[Optional["Group"]] = relationship("Group", back_populates="users")
    
    # Методы сериализации
    def to_dict(self):
        """
        Сериализация модели пользователя в словарь
        """
        return {
            "id": str(self.id),
            "login": self.login,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "department_id": str(self.department_id) if self.department_id else None,
            "group_id": str(self.group_id) if self.group_id else None,
            "work_position": self.work_position,
            "date_employment": self.date_employment.isoformat() if self.date_employment else None,
            "city": self.city.value if self.city else None,
            "date_birthday": self.date_birthday.isoformat() if self.date_birthday else None,
            "company": self.company.value if self.company else None,
            "bitrix_id": self.bitrix_id,
            "user_email": self.user_email,
            "telegram_id": self.telegram_id,
            "gender": self.gender.value if self.gender else None,
            "photo_url": self.photo_url,
            "photo_url_small": self.photo_url_small,
            "bio": self.bio,
            "role": self.role.value,
            "additional_role": self.additional_role.value if self.additional_role else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }
    
    # Сериализация модели пользователя в словарь с публичными данными
    def to_public_dict(self):
        """
        Сериализация модели пользователя в словарь с публичными данными
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "work_position": self.work_position,
            "department": self.department.name if self.department else None,
            "group": self.group.name if self.group else None,
            "city": self.city.value if self.city else None,
            "company": self.company.value if self.company else None,
            "user_email": self.user_email,
            "photo_url": self.photo_url,
            "photo_url_small": self.photo_url_small,
            "bio": self.bio
        }
