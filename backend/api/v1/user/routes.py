from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import List, Tuple

from .schemas import  UserFilter, UserProfilesResponse, UserProfileResponse, UserUpdateCombined
from api.v1.schemas import MessageResponse, TokenPayload
from .services import UserService
from core.extensions.logger import logger
from api.v1.dependencies import (
    get_db, get_redis, jwt_handler, require_not_guest, get_current_user_payload, 
    require_authenticated, require_admin_roles
)
from api.v1.telegram.schemas import ChannelRuleResponse

user_router = APIRouter(prefix="/api/v1/users", tags=["Управление пользователями"])

# Создает экземпляр сервиса пользователей
def _create_user_service(db: AsyncSession, redis: Redis) -> UserService:
    """
    Создает экземпляр сервиса пользователей
    """
    return UserService(db, jwt_handler, redis)

# Обрабатывает исключения пользователей
def _handle_user_exception(err: Exception, error_message: str) -> None:
    """
    Обрабатывает исключения пользователей
    """
    if isinstance(err, HTTPException):
        raise err
    logger.error(f"{error_message}: {err}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=error_message
    )

# Валидирует ID пользователя и сессии
def _validate_user_ids(current_user: TokenPayload) -> Tuple[str, str]:
    """
    Валидирует ID пользователя и сессии
    """
    try:
        return True
    except ValueError as err:
        logger.error(f"Ошибка валидации ID: {err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невалидный ID пользователя"
        )

# Получает информацию о пользователе по ID
@user_router.get(
    "/{user_id}",
    response_model=UserProfileResponse,
    summary="Получение информации о пользователе"
)
@require_not_guest()
async def get_user_by_id(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: TokenPayload = Depends(get_current_user_payload),
) -> UserProfileResponse:
    """
    Авторизованный API. Доступ: `Администраторы`, `Руководители`, `Сотрудники`\n
    Для администраторов возвращается `UserPrivateProfile`, для остальных `UserPublicProfile`\n
    Получение информации о пользователе по ID
    """
    try:
        _validate_user_ids(current_user)
        user_service = _create_user_service(db, redis)
        return await user_service.get_user_by_id(user_id, current_user)
    
    except Exception as err:
        _handle_user_exception(err, "Ошибка при получении информации о пользователе")

# Получает список пользователей с фильтрацией и пагинацией
@user_router.get(
    "",
    response_model=UserProfilesResponse,
    summary="Получение списка пользователей"
)
@require_not_guest()
async def get_users(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user_filter: UserFilter = Depends(),
    current_user: TokenPayload = Depends(get_current_user_payload),
) -> UserProfilesResponse:
    """
    Авторизованный API. Доступ: `Администраторы`, `Руководители`, `Сотрудники`\n
    Для администраторов возвращаются `UserPrivateProfile`, для остальных `UserPublicProfile`\n
    Получение списка пользователей c фильтрацией и пагинацией
    """
    try:
        user_service = _create_user_service(db, redis)
        return await user_service.get_users(user_filter, current_user)
    
    except Exception as err:
        _handle_user_exception(err, "Ошибка при получении списка пользователей")

# Обновляет информацию о пользователе
@user_router.put(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Обновление информации о пользователе"
)
@require_authenticated()
async def update_user(
    request: Request,
    user_id: str,
    user_data: UserUpdateCombined,
    current_user: TokenPayload = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    """
    Авторизованный API. Доступ: `Администраторы`, `Руководители`, `Сотрудники`, `Гости`\n
    У Администраторов обновление всех полей `UserUpdateCombined`\n
    Обновление информации о пользователе
    """
    try:
        _validate_user_ids(current_user)
        user_service = _create_user_service(db, redis)
        return await user_service.update_user(user_id, user_data, current_user)
    
    except Exception as err:
        _handle_user_exception(err, "Ошибка при обновлении информации о пользователе")

# Деактивирует пользователя
@user_router.put(
    "/{user_id}/deactivate",
    response_model=MessageResponse,
    summary="Деактивация пользователя"
)
@require_admin_roles()
async def deactivate_user(
    request: Request,
    user_id: str,
    current_user: TokenPayload = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    """
    Авторизованный API. Доступ: `Администраторы`\n
    Деактивация аккаунта пользователя
    """
    try:
        _validate_user_ids(current_user)
        user_service = _create_user_service(db, redis)
        return await user_service.deactivate_user(user_id, current_user)
    
    except Exception as err:
        _handle_user_exception(err, "Ошибка при деактивации пользователя")

# Активация пользователя
@user_router.put(
    "/{user_id}/activate",
    response_model=MessageResponse,
    summary="Активация пользователя"
)
@require_admin_roles()
async def activate_user(
    request: Request,
    user_id: str,
    current_user: TokenPayload = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    """
    Авторизованный API. Доступ: `Администраторы`\n
    Активация аккаунта пользователя
    """
    try:
        _validate_user_ids(current_user)
        user_service = _create_user_service(db, redis)
        return await user_service.activate_user(user_id, current_user)
    
    except Exception as err:
        _handle_user_exception(err, "Ошибка при активации пользователя")

# Удаляет пользователя
@user_router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Удаление пользователя"
)
@require_admin_roles(allowed_roles=["superadmin"])
async def delete_user(
    request: Request,
    user_id: str,
    current_user: TokenPayload = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    """
    Авторизованный API. Доступ: `Администраторы`\n
    Удаление аккаунта пользователя
    """
    try:
        _validate_user_ids(current_user)
        user_service = _create_user_service(db, redis)
        return await user_service.delete_user(user_id, current_user)
    
    except Exception as err:
        _handle_user_exception(err, "Ошибка при удалении пользователя")

# Получает список ТГ-групп пользователя
@user_router.get(
    "/{user_id}/telegram",
    response_model=List[ChannelRuleResponse],
    summary="Получение ТГ-групп пользователя"
)
@require_not_guest()
async def get_user_telegram_rules(
    request: Request,
    user_id: str,
    current_user: TokenPayload = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> List[ChannelRuleResponse]:
    """
    Авторизованный API. Доступ: `Администраторы`, `Руководители`, `Сотрудники`\n
    Получение ТГ-групп, в которые должен входить пользователь
    """
    try:
        _validate_user_ids(current_user)
        user_service = _create_user_service(db, redis)
        return await user_service.get_user_telegram_rules(user_id, current_user)
    
    except Exception as err:
        _handle_user_exception(err, "Ошибка при получении ТГ-групп пользователя")

# Удаляет пользователя из ТГ-группы
@user_router.delete(
    "/{user_id}/telegram",
    response_model=MessageResponse,
    summary="Удаление из ТГ-группы"
)
@require_admin_roles()
async def delete_user_from_telegram(
    request: Request,
    user_id: str,
    current_user: TokenPayload = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    """
    Авторизованный API. Доступ: `Администраторы`\n
    Удаление из ТГ-группы
    """
    try:
        _validate_user_ids(current_user)
        user_service = _create_user_service(db, redis)
        return await user_service.delete_user_from_telegram(user_id, current_user)
    
    except Exception as err:
        _handle_user_exception(err, "Ошибка при удалении из ТГ-группы")   
