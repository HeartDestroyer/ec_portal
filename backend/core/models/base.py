from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData

convention = {
    "ix": "ix_%(column_0_label)s",  # Имя индекса
    "uq": "uq_%(table_name)s_%(column_0_name)s",  # Имя уникального ограничения
    "ck": "ck_%(table_name)s_%(constraint_name)s",  # Имя CHECK ограничения
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",  # Имя внешнего ключа
    "pk": "pk_%(table_name)s"  # Имя первичного ключа
}

metadata = MetaData(naming_convention=convention)
Base = declarative_base(metadata=metadata)
