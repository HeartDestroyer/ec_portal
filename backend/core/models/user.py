import enum
import uuid
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, Date, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from models.base import Base
from models.department import Department
from models.group import Group
from models.session import Session
from models.telegram import ChannelRule

class Role(enum.Enum):
    SUPER_ADMIN = "superadmin"
    ADMIN = "admin"
    LEADER = "leader"
    EMPLOYEE = "employee"
    GUEST = "guest"

class AdditionalRole(enum.Enum):
    COORDINATOR_OTS = "coordinator_ots"
    COORDINATOR_OP = "coordinator_op"

class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"

class Company(enum.Enum):
    ITSK = 'ООО "ИТСК"'
    EC_TECHNOLOGIES = 'ООО "ЭЦ-Технологии"'
    EXPERT_CENTER_FINANCE = 'ООО УК "ЭкспертЦентрФинанс"'
    EXPERT_CENTER_SAMARA = 'ООО "Эксперт Центр Самара"'
    NEC = 'ООО "НЭЦ"'
    EEC = 'ООО "ЕЭЦ"'
    ECSP = 'ООО "ЭЦСП"'
    ENN = 'ООО "ЭНН"'

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


class User(Base):
    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4, doc="ID пользователя")
    login: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True, doc="Логин пользователя")
    email: Mapped[str] = mapped_column(String(256), unique=True, nullable=False, index=True, doc="Электронная почта пользователя")
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True, doc="Имя пользователя")
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False, doc="Хэшированный пароль пользователя")
    phone: Mapped[Optional[str]] = mapped_column(String(25), nullable=True, default=None, index=True, doc="Телефон пользователя")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, doc="Активен ли пользователь")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, doc="Верифицирован ли пользователь")

    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey('departments.id'), nullable=True, doc="ID департамента")
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey('groups.id'), nullable=True, doc="ID группы")

    work_position: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, doc="Должность пользователя")
    date_employment: Mapped[Optional[date]] = mapped_column(Date, nullable=True, doc="Дата трудоустройства пользователя")
    city: Mapped[Optional[City]] = mapped_column(Enum(City), nullable=True, index=True, doc="Город пользователя")
    date_birthday: Mapped[Optional[date]] = mapped_column(Date, nullable=True, doc="Дата рождения пользователя")
    company: Mapped[Optional[Company]] = mapped_column(Enum(Company), nullable=True, index=True, doc="Компания пользователя")
    bitrix_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True, doc="ID в Битриксе")
    qr_code_vcard: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, doc="QR-код vCard")
    user_email: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, doc="Рабочая почта пользователя")
    telegram_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True, doc="Телеграм ID")
    gender: Mapped[Optional[Gender]] = mapped_column(Enum(Gender), nullable=True, index=True, doc="Пол")
    photo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, doc="URL фотографии пользователя")
    photo_url_small: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, doc="URL уменьшенной фотографии пользователя")
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True, doc="Биография или описание пользователя")

    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.GUEST, nullable=False, index=True, doc="Роль пользователя")
    additional_role: Mapped[Optional[AdditionalRole]] = mapped_column(Enum(AdditionalRole), nullable=True, index=True, doc="Дополнительная роль пользователя")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, doc="Дата создания пользователя")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, doc="Дата обновления пользователя")
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, doc="Дата последнего входа в систему")
    failed_login_attempts: Mapped[int] = mapped_column(default=0, doc="Количество неудачных попыток входа в систему")
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, doc="Дата блокировки пользователя")
    last_password_change: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, doc="Дата последнего изменения пароля")
    totp_secret: Mapped[Optional[str]] = mapped_column(String, nullable=True, doc="Секретный ключ TOTP")
    is_2fa_enabled: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, doc="Включено ли двухфакторное подтверждение")

    crm_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True, doc="ID в CRM")
    old_id: Mapped[Optional[int]] = mapped_column(default=None, nullable=True, index=True, doc="ID в старой системе")

    department: Mapped[Optional["Department"]] = relationship("Department", back_populates="users", doc="Департамент пользователя")
    group: Mapped[Optional["Group"]] = relationship("Group", back_populates="users", doc="Группа пользователя")
    sessions: Mapped[List["Session"]] = relationship("Session", back_populates="user", cascade="all, delete-orphan", doc="Сессии пользователя")
    channel_rules: Mapped[List["ChannelRule"]] = relationship(
        secondary="channel_tg_rule_users",
        back_populates="users",
        doc="Правила Telegram-чатов, применимые к пользователю"
    )
