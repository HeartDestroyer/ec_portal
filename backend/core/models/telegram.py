import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey, Table, Column
import enum
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import DateTime, String, Enum, BigInteger

from core.models.base import Base
from core.models.department import Department
from core.models.group import Group

if TYPE_CHECKING:
    from core.models.user import User

class RuleType(enum.Enum):
    BASE = 'base'
    CITY = 'city'
    GENDER = 'gender'
    DEPARTMENT = 'department'
    GROUP = 'group'
    MANUAL = 'manual'

class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"

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


# Таблица связи многие-ко-многим
channel_rule_users = Table(
    'channel_tg_rule_users',
    Base.metadata,
    Column('channel_rule_id', UUID(as_uuid=True), ForeignKey('channel_tg_rules.id'), primary_key=True),
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
)


class ChannelRule(Base):
    __tablename__ = 'channel_tg_rules'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4, doc="ID правила")
    rule_type: Mapped[RuleType] = mapped_column(Enum(RuleType), nullable=False, doc="Тип правила, определяет какие пользователи будут приглашены")
    city: Mapped[Optional[City]] = mapped_column(Enum(City), nullable=True, doc="Город для city-правил")
    gender: Mapped[Optional[Gender]] = mapped_column(Enum(Gender), nullable=True, doc="Гендер для gender-правил")
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey('departments.id'), nullable=True, doc="ID департамента")
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey('groups.id'), nullable=True, doc="ID группы")
    channel_name: Mapped[str] = mapped_column(String(100), nullable=False, doc="Название чата")
    channel_url: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, doc="Пригласительная ссылка")
    chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, doc="ID Telegram-чата")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, doc="Дата создания правила")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, doc="Дата обновления правила")

    # Связь с пользователями для ручного добавления
    users: Mapped[List["User"]] = relationship(
        secondary=channel_rule_users,
        back_populates="channel_rules",
        doc="Пользователи, которых нужно пригласить вручную, независимо от других критериев"
    )

    department: Mapped[Optional["Department"]] = relationship("Department", back_populates="channel_tg_rules", doc="Департамент, который будет приглашен в чат")
    group: Mapped[Optional["Group"]] = relationship("Group", back_populates="channel_tg_rules", doc="Группа, которая будет приглашена в чат")
