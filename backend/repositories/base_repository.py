# backend/repositories/base_repository.py - Базовый репозиторий для CRUD операций

from abc import ABC
from typing import Generic, TypeVar, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)

class BaseRepository(ABC, Generic[ModelType]):
    """
    Базовый репозиторий для CRUD операций

    Методы:
        - `get_by_id` - Получить объект по ID
        - `get_all` - Получить все объекты с пагинацией
        - `create` - Создать новый объект
        - `update` - Обновить объект
        - `delete` - Удалить объект
    """
    
    def __init__(self, session: AsyncSession, model: type[ModelType]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: str) -> Optional[ModelType]:
        """
        Получить объект по ID\n
        `id` - ID объекта
        """
        return await self.session.get(self.model, id)

    async def get_all(self, offset: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Получить все объекты с пагинацией\n
        `offset` - Количество пропущенных объектов\n
        `limit` - Количество объектов на странице
        """
        query = select(self.model).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, obj_data: dict) -> ModelType:
        """
        Создать новый объект\n
        `obj_data` - Данные объекта
        """
        obj = self.model(**obj_data)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def update(self, id: str, obj_data: dict) -> Optional[ModelType]:
        """
        Обновить объект\n
        `id` - ID объекта\n
        `obj_data` - Данные объекта
        """
        query = update(self.model).where(self.model.id == id).values(**obj_data)
        await self.session.execute(query)
        await self.session.commit()
        return await self.get_by_id(id)

    async def delete(self, id: str) -> bool:
        """
        Удалить объект\n
        `id` - ID объекта
        """
        query = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0
