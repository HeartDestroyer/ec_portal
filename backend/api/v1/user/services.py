from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Dict, Any, List, Optional, Union, TypedDict
import aiohttp
from redis.asyncio import Redis
from enum import Enum

from api.v1.auth.services import AuthenticationService
from api.v1.dependencies import settings
from core.models.user import User
from core.models.department import Department
from core.models.group import Group
from .schemas import (
    UserFilter, UserPrivateProfile, UserPublicProfile, UserProfilesResponse, UserProfileResponse, UserUpdateCombined
)
from api.v1.schemas import MessageResponse, TokenPayload
from core.extensions.logger import logger
from core.security.jwt import JWTHandler

# Сервис для работы с данными пользователя и пользователем
class UserService:
    """
    Сервис для работы с данными пользователя и пользователем

    :`get_users`: - Получение списка пользователей с фильтрацией и пагинацией
    :`get_user_by_id`: - Получение пользователя по ID
    :`update_user`: - Обновление данных пользователя
    :`deactivate_user`: - Деактивация пользователя
    :`activate_user`: - Активация пользователя
    :`sync_user_with_bitrix`: - Синхронизация данных пользователя с Битрикс
    :`get_info_crm`: - Получение информации о пользователе из CRM по ID
    :`get_info_bitrix`: - Получение информации о пользователе из Битрикс по ID
    :`deactivate_user`: - Деактивация пользователя
    :`activate_user`: - Активация пользователя
    """

    # Инициализация
    def __init__(self, db: AsyncSession, jwt_handler: JWTHandler, redis: Redis):
        self.db = db
        self.jwt_handler = jwt_handler
        self.redis = redis
        self.bitrix_url = settings.BITRIX_WEBHOOK_URL + "/user.search.json"
        self.admin_roles = settings.ADMIN_ROLES
        self.auth_service = AuthenticationService(db, jwt_handler, redis, None)

    # Проверяет, является ли пользователь администратором
    def _is_admin(self, user: User) -> bool:
        """
        Проверяет, является ли пользователь администратором
        """
        return user.role in self.admin_roles

    # Строит запросы для получения пользователей и их количества
    def _build_user_query(self, filter: UserFilter) -> tuple[select, select]:
        """
        Строит запросы для получения пользователей и их количества
        """
        query = select(User)
        count_query = select(func.count(User.id))
        conditions = []

        if filter.name:
            search_term = f"%{filter.name}%"
            conditions.append(User.name.ilike(search_term))

        if filter.department:
            conditions.append(User.department == filter.department)

        if filter.group:
            conditions.append(User.group == filter.group)

        if filter.city:
            conditions.append(User.city == filter.city.name)

        if filter.company:
            conditions.append(User.company == filter.company.name)

        if filter.bitrix_id is not None:
            conditions.append(User.bitrix_id == filter.bitrix_id)

        if filter.crm_id:
            conditions.append(User.id == filter.crm_id)

        if filter.gender:
            conditions.append(User.gender == filter.gender.name)

        if filter.role:
            conditions.append(User.role == filter.role.name)

        if filter.is_active is not None:
            conditions.append(User.is_active == filter.is_active)

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        return query, count_query

    async def get_users(self, filter: UserFilter, current_user: TokenPayload) -> UserProfilesResponse:
        """
        Получение списка пользователей с фильтрацией и пагинацией
        """
        try:
            query, count_query = self._build_user_query(filter)
            total_count = await self.db.scalar(count_query)

            query = query.offset((filter.page - 1) * filter.limit).limit(filter.limit)
            result = await self.db.execute(query)
            users = result.scalars().all()

            is_admin = self._is_admin(current_user)
            profile_class = UserPrivateProfile if is_admin else UserPublicProfile

            # Преобразуем UUID в строки перед созданием ответа
            user_profiles = []
            for user in users:
                user_dict = user.__dict__.copy()
                user_dict['id'] = str(user.id)
                if hasattr(user, 'user_id'):
                    user_dict['user_id'] = str(user.user_id)
                user_profiles.append(profile_class.model_validate(user_dict))

            return UserProfilesResponse(
                users=user_profiles,
                total_users=total_count
            )

        except Exception as err:
            logger.error(f"Ошибка при получении списка пользователей: {err}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при получении списка пользователей"
            )

    # Получает пользователя по ID
    async def get_user_by_id(self, user_id: str, current_user: TokenPayload) -> UserProfileResponse:
        """
        Получение пользователя по ID\n
        Для администраторов возвращается `UserPrivateProfile`, для остальных — `UserPublicProfile`\n

        `user_id` - ID пользователя\n
        `current_user` - Текущий пользователь\n
        :return: Объект пользователя
        :raises HTTPException: Если пользователь не найден
        """
        try:
            query = select(User).where(User.id == user_id)
            result = await self.db.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Пользователь не найден"
                )

            is_admin = self._is_admin(current_user)
            profile_class = UserPrivateProfile if is_admin else UserPublicProfile

            # Преобразуем UUID в строку перед созданием ответа
            user_dict = user.__dict__.copy()
            user_dict['id'] = str(user.id)
            if hasattr(user, 'user_id'):
                user_dict['user_id'] = str(user.user_id)

            return UserProfileResponse(user=profile_class.model_validate(user_dict))

        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"Ошибка при получении пользователя по ID {user_id}: {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при получении данных пользователя"
            )

    # Проверяет существование пользователя
    async def _check_user_exists(self, user_id: str) -> User:
        """
        Проверяет существование пользователя

        `user_id` - ID пользователя\n
        :return: Объект пользователя
        :raises HTTPException: Если пользователь не найден
        """
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )

        return user

    # Проверяет права доступа к пользователю
    async def _check_user_access(self, user_id: str, current_user: TokenPayload) -> None:
        """
        Проверяет права доступа к пользователю\n

        `user_id` - ID пользователя\n
        `current_user` - Текущий пользователь\n
        :raises HTTPException: Если пользователь не найден
        """
        is_admin = self._is_admin(current_user)
        if not is_admin and str(current_user.id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы можете обновлять только свои данные"
            )

    # Проверяет уникальность email и login
    async def _check_unique_fields(self, user: User, update_data: Dict[str, Any]) -> None:
        """
        Проверяет уникальность email и login

        `user` - Пользователь\n
        `update_data` - Данные для обновления пользователя\n
        :raises HTTPException: Если пользователь с такой почтой или логином уже существует
        """
        if update_data.get('email') and update_data['email'] != user.email:
            existing_user = await self.auth_service.get_user_by_login_or_email(update_data['email'])
            if existing_user and existing_user.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Пользователь с такой почтой уже существует"
                )

        if update_data.get('login') and update_data['login'] != user.login:
            existing_user = await self.auth_service.get_user_by_login_or_email(update_data['login'])
            if existing_user and existing_user.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Пользователь с таким логином уже существует"
                )

    # Проверяет существование связанных сущностей
    async def _check_related_entities(self, update_data: Dict[str, Any]) -> None:
        """
        Проверяет существование связанных сущностей

        `update_data` - Данные для обновления пользователя\n
        :raises HTTPException: Если связанная сущность не найдена
        """
        if update_data.get('department_id'):
            dept_query = select(Department).where(Department.id == update_data['department_id'])
            dept_result = await self.db.execute(dept_query)
            if not dept_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Указанный департамент не существует"
                )

        if update_data.get('group_id'):
            group_query = select(Group).where(Group.id == update_data['group_id'])
            group_result = await self.db.execute(group_query)
            if not group_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Указанная группа не существует"
                )

    # Логирует изменения в данных пользователя
    async def _log_user_changes(self, user: User, update_data: Dict[str, Any]) -> List[str]:
        """
        Логирует изменения в данных пользователя

        `user` - Пользователь\n
        `update_data` - Данные для обновления пользователя\n
        :return: Список изменений
        """
        changes = []
        for key, value in update_data.items():
            if hasattr(user, key):
                old_value = getattr(user, key)
                if old_value != value:
                    changes.append(f"{key}: {old_value} -> {value}")
                    if isinstance(value, Enum):
                        update_data[key] = value.name
                    setattr(user, key, update_data[key])
        return changes

    # Обновляет информацию о пользователе
    async def update_user(self, user_id: str, user_data: UserUpdateCombined, current_user: TokenPayload) -> MessageResponse:
        """
        Обновление информации о пользователе

        `user_id` - ID пользователя\n
        `user_data` - Данные для обновления пользователя\n
        `current_user` - Текущий пользователь\n
        :return: Сообщение об успешном обновлении
        """
        try:
            user = await self._check_user_exists(user_id)
            await self._check_user_access(user_id, current_user)

            user_data.__pydantic_validator_config__ = {"context": {"current_user": current_user}}
            update_data = user_data.model_dump(exclude_unset=True)

            await self._check_unique_fields(user, update_data)
            await self._check_related_entities(update_data)

            changes = await self._log_user_changes(user, update_data)
            await self.db.commit()

            if changes:
                logger.info(f"Пользователь {user_id} обновлен. Изменения: {', '.join(changes)}")

            return MessageResponse(message="Данные пользователя успешно обновлены")

        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"Ошибка при обновлении пользователя {user_id}: {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при обновлении данных пользователя"
            )

    # Деактивирует пользователя
    async def deactivate_user(self, user_id: str, current_user: TokenPayload) -> MessageResponse:
        """
        Деактивация пользователя

        `user_id` - ID пользователя\n
        `current_user` - Текущий пользователь\n
        :return: Сообщение об успешной деактивации
        """
        try:
            user = await self._check_user_exists(user_id)
            await self._check_user_access(user_id, current_user)

            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Пользователь уже деактивирован"
                )

            user.is_active = False
            user.is_verified = False
            user.deactivated_at = datetime.utcnow()
            await self.db.commit()

            logger.info(f"Пользователь {user_id} деактивирован")
            return MessageResponse(message="Пользователь успешно деактивирован")

        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"Ошибка при деактивации пользователя {user_id}: {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при деактивации пользователя"
            )

    # Активирует пользователя
    async def activate_user(self, user_id: str, current_user: TokenPayload) -> MessageResponse:
        """
        Активация пользователя

        `user_id` - ID пользователя\n
        `current_user` - Текущий пользователь\n
        :return: Сообщение об успешной активации
        """
        try:
            user = await self._check_user_exists(user_id)
            await self._check_user_access(user_id, current_user)

            if user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Пользователь уже активирован"
                )

            user.is_active = True
            user.is_verified = True
            user.deactivated_at = None
            await self.db.commit()

            logger.info(f"Пользователь {user_id} активирован")
            return MessageResponse(message="Пользователь успешно активирован")

        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"Ошибка при активации пользователя {user_id}: {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при активации пользователя"
            )

    # Удаляет пользователя
    async def delete_user(self, user_id: str, current_user: TokenPayload) -> MessageResponse:
        """
        Удаление пользователя

        `user_id` - ID пользователя\n
        `current_user` - Текущий пользователь\n
        :return: Сообщение об успешном удалении
        """
        try:
            user = await self._check_user_exists(user_id)
            await self._check_user_access(user_id, current_user)

            await self.db.delete(user)
            await self.db.commit()

            logger.info(f"Пользователь {user_id} удален")
            return MessageResponse(message="Пользователь успешно удален")

        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"Ошибка при удалении пользователя {user_id}: {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при удалении пользователя"
            )

    # Получает информацию о пользователе из CRM
    async def get_info_crm(self, user_id: str) -> Dict[str, Any]:
        """
        Получение информации о пользователе из CRM

        `user_id` - ID пользователя\n
        :return: Информация о пользователе
        """
        pass

    # Получает информацию о пользователе из Битрикс
    async def get_info_bitrix(self, bitrix_id: int) -> Dict[str, Any]:
        """
        Получение информации о пользователе из Битрикс

        `bitrix_id` - ID пользователя в Битрикс\n
        Возвращает информацию о пользователе
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.bitrix_url,
                    params={"ID": bitrix_id}
                ) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Ошибка при получении данных из Битрикс"
                        )

                    data = await response.json()
                    if not data.get("result"):
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Пользователь не найден в Битрикс"
                        )

                    user_data = data["result"][0]
                    return {
                        "id": user_data.get("ID"),
                        "name": user_data.get("NAME"),
                        "last_name": user_data.get("LAST_NAME"),
                        "email": user_data.get("EMAIL"),
                        "phone": user_data.get("PERSONAL_PHONE"),
                        "department": user_data.get("UF_DEPARTMENT"),
                        "position": user_data.get("POSITION"),
                        "is_active": user_data.get("ACTIVE") == "Y"
                    }

        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"Ошибка при получении информации из Битрикс для пользователя {bitrix_id}: {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при получении информации из Битрикс"
            )

    # Синхронизирует данные пользователя с Битрикс
    async def sync_user_with_bitrix(self, user_id: str) -> User:
        """
        Синхронизация данных пользователя с Битрикс

        `user_id` - ID пользователя\n
        :return: Пользователь
        """
        pass