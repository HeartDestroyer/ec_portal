from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from core.extensions.logger import logger
import uuid


# Схемы
from .schemas import (
    SessionFilter, SessionsPage, MessageResponse
)

# Сервисы и зависимости
from .services import SessionService

# Зависимости
from api.v1.dependencies import (
    get_db, get_redis, settings, require_admin_roles, jwt_handler
)

session_router = APIRouter(prefix="/api/v1/session", tags=["Управление сессиями пользователей"])

# Универсальный эндпоинт для получения сессий
@session_router.get(
    "/sessions",
    response_model=SessionsPage,
    summary="Получение списка сессий"
)
async def get_sessions(
    request: Request,
    filter: SessionFilter = Depends(),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """
    Получение списка сессий\n
    - Для обычных пользователей: только свои сессии с фильтрацией по активности\n
    - Для админов: все сессии с фильтрацией по имени пользователя и активности\n
    Требуется валидный `refresh_token` в куки
    """
    try:
        refresh_token = request.cookies.get(jwt_handler.refresh_cookie_name)
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh токен отсутствует"
            )

        payload = await jwt_handler.verify_token(refresh_token, "refresh", redis)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный refresh токен"
            )

        user_id = payload.get("id")
        user_role = payload.get("role")
        session_id = payload.get("session_id")

        if not user_id or not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный refresh токен"
            )

        # Проверяем валидность сессии
        session_service = SessionService(db, jwt_handler)
        session_service.jwt_handler.request = request
        if not await session_service.check_session_validity(str(session_id)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Сессия истекла или неактивна"
            )

        if user_role not in settings.ADMIN_ROLES:
            filter.user_id = user_id
            filter.user_name = None
        elif not filter.user_id:
            filter.user_id = None

        return await session_service.get_sessions(filter, str(session_id))

    except HTTPException as err:
        raise err
    except Exception as err:
        logger.error(f"Ошибка при получении списка сессий: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении списка сессий"
        )

# Завершение конкретной сессии
@session_router.delete(
    "/sessions/{session_id}",
    response_model=MessageResponse,
    summary="Завершение конкретной сессии"
)
async def deactivate_session(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """ 
    Завершение конкретной сессии пользователя по ID сессии `session_id`.
    Требуется валидный `refresh_token` в куки.
    Завершить сессию может: Владелец сессии, Администратор
    """
    try:
        uuid.UUID(session_id)
        
        # Получаем токен и проверяем его
        refresh_token = request.cookies.get(jwt_handler.refresh_cookie_name)
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh токен отсутствует"
            )

        # Проверяем refresh токен
        payload = await jwt_handler.verify_token(refresh_token, "refresh", redis)
        user_id = payload.get("id")
        user_role = payload.get("role")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный refresh токен"
            )

        session_service = SessionService(db, jwt_handler)
        await session_service.deactivate_session(session_id, user_id, user_role)
        return MessageResponse(message=f"Сессия пользователя успешно завершена")

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат ID сессии"
        )
    except HTTPException as err:
        raise err
    except Exception as err:
        logger.error(f"Ошибка при завершении сессии: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при завершении сессии"
        )

# Завершение всех других сессий, кроме текущей
@session_router.delete(
    "/sessions",
    response_model=MessageResponse,
    summary="Завершение всех других сессий, кроме текущей"
)
async def terminate_other_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """
    Завершение всех сессий пользователя кроме текущей.
    Требуется валидный `refresh_token` в куки
    """
    try:
        refresh_token = request.cookies.get(jwt_handler.refresh_cookie_name)
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh токен отсутствует"
            )

        # Проверяем refresh токен
        payload = await jwt_handler.verify_token(refresh_token, "refresh", redis)
        user_id = payload.get("id")
        current_session_id = payload.get("session_id")

        if not user_id or not current_session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный refresh токен"
            )

        # Проверяем валидность текущей сессии
        session_service = SessionService(db, jwt_handler)
        if not await session_service.check_session_validity(current_session_id):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Текущая сессия истекла или неактивна"
            )

        # Завершаем все остальные сессии
        await session_service.terminate_other_sessions(current_session_id, user_id)
        return MessageResponse(message="Все остальные сессии успешно завершены")

    except HTTPException as err:
        raise err
    except Exception as err:
        logger.error(f"Ошибка при завершении других сессий: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при завершении других сессий"
        )
