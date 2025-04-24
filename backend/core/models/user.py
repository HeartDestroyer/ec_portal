# backend/core/models/user.py

import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.models.base import Base

# Роли пользователей
class Role(enum.Enum):
    SUPER_ADMIN = "super_admin"
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

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    login = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(256), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False, index=True)
    hashed_password = Column(String(256), nullable=False)
    phone = Column(String(25), nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True, doc="ID департамента")
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=True, doc="ID группы")

    work_position = Column(String(128), nullable=True, doc="Должность")
    date_employment = Column(Date, nullable=True, doc="Дата трудоустройства")
    city = Column(SQLEnum(City), nullable=True, index=True, doc="Город")
    date_birthday = Column(Date, nullable=True, doc="Дата рождения")
    company = Column(SQLEnum(Company), nullable=True, index=True, doc="Компания")
    bitrix_id = Column(Integer, nullable=True, index=True, doc="ID в Битриксе")
    qr_code_vcard = Column(String(512), nullable=True, doc="QR-код vCard")
    user_email = Column(String(128), nullable=True, doc="Рабочая почта")
    telegram_id = Column(String(128), nullable=True, index=True, doc="Телеграм ID")
    gender = Column(SQLEnum(Gender), nullable=True, index=True, doc="Пол")
    photo_url = Column(String(512), nullable=True, doc="URL фотографии пользователя")
    photo_url_small = Column(String(512), nullable=True, doc="URL уменьшенной фотографии пользователя")
    bio = Column(Text, nullable=True, doc="Биография или описание пользователя")

    role = Column(SQLEnum(Role), default=Role.GUEST, nullable=False, index=True, doc="Роль")
    additional_role = Column(SQLEnum(AdditionalRole), nullable=True, index=True, doc="Дополнительная роль")

    # Поля для безопасности и аудита
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    last_password_change = Column(DateTime, nullable=True, doc="Дата последнего изменения пароля")

    # Связи
    department = relationship("Department", back_populates="users")
    group = relationship("Group", back_populates="users")
    
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
            "department_id": self.department_id,
            "group_id": self.group_id,
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
