# backend/core/models/user.py

import enum
import uuid
from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Enum as SQLEnum, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Стандартные роли пользователей
class RoleEnum(enum.Enum):
    ADMIN = "admin"
    RUKOVOD = "rukovod"
    WORKER = "worker"
    GUEST = "guest"

# Расширенные роли пользователей
class DopRoleEnum(str, enum.Enum):
    COORDINATOR_OTS = "coordinatorOTS"

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(256), unique=True, nullable=False, index=True)
    hashed_password = Column(String(256), nullable=False) # Переименовано из 'password'
    name = Column(String(128), nullable=False, index=True)
    phone = Column(String(25), nullable=True, index=True)
    is_active = Column(Boolean, default=True) # Стандартное поле для активации
    is_verified = Column(Boolean, default=False) # Для подтверждения email

    # Поля из вашей существующей модели (добавляем нужные)
    workPosition = Column(String(128), nullable=True, doc="Должность")
    departament = Column(Integer, nullable=True, doc="ID департамента") # Возможно ForeignKey
    company = Column(String(80), nullable=True, doc="Компания")
    dateEmployment = Column(Date, nullable=True, doc="Дата приема на работу")
    city = Column(String(30), nullable=True, doc="Город")
    dateBirthday = Column(Date, nullable=True, doc="Дата рождения")
    # Используем Enum из SQLAlchemy для хранения ролей
    role = Column(SQLEnum(RoleEnum), default=RoleEnum.GUEST, nullable=False, index=True, doc="Основная роль")
    dop_role = Column(SQLEnum(DopRoleEnum), nullable=True, index=True, doc="Дополнительная роль")
    bitrixId = Column(Integer, nullable=True, index=True, doc="ID в Битрикс")
    user_email = Column(String(128), nullable=True, doc="Рабочая почта сотрудника") # Возможно, дублирует 'email'?
    telegram_id = Column(String(128), nullable=True, index=True, doc="Телеграм ID")
    gender = Column("gender", String(10), nullable=True, default=None, doc="Пол: male/female") # Переименовано из _gender
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, doc="UUID сотрудника")

    # Поля для безопасности и аудита
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
