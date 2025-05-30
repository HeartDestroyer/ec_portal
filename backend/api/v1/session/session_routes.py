# backend/api/v1/session/session_routes.py - Маршруты для управления сессиями пользователей

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.dependencies import settings, require_authenticated, handle_exception, get_current_user_payload, MessageResponse, TokenPayload
from api.v1.session.schemas import SessionFilter, SessionsPage, SessionResponse, UserAgentInfo
from api.v1.session.services import SessionService
from api.v1.session.dependencies import get_session_repository, create_session_service

session_router = APIRouter(prefix="/api/v1/session", tags=["Управление сессиями пользователей"])

@session_router.get(
    "",
    response_model=SessionsPage,
    summary="Получение списка сессий"
)
@require_authenticated()
async def get_sessions(
    request: Request,
    current_user: TokenPayload = Depends(get_current_user_payload),
    filter: SessionFilter = Depends(),
    session_service: SessionService = Depends(create_session_service),
) -> SessionsPage:
    """
    Авторизованный API. Доступ: `Администраторы`, `Руководители`, `Сотрудники`, `Гости`\n
    Получение списка сессий\n
        - Для обычных пользователей: только свои сессии с фильтрацией по активности\n
        - Для администраторов: все сессии с фильтрацией по имени пользователя и активности
    """
    try:
        if current_user.role not in settings.ADMIN_ROLES:
            filter.user_id = current_user.user_id
            filter.user_name = None
        elif not filter.user_id:
            filter.user_id = None
            
        return await session_service.get_sessions_filtered(filter, current_user.session_id)
    
    except Exception as err:
        handle_exception(err, "Ошибка при получении списка сессий", status.HTTP_500_INTERNAL_SERVER_ERROR)

@session_router.delete(
    "",
    response_model=MessageResponse,
    summary="Завершение всех своих сессий, кроме текущей"
)
@require_authenticated()
async def terminate_other_sessions(
    request: Request,
    current_user: TokenPayload = Depends(get_current_user_payload),
    session_service: SessionService = Depends(create_session_service),
) -> MessageResponse:
    """
    Авторизованный API. Доступ: `Администраторы`, `Руководители`, `Сотрудники`, `Гости`\n
    Завершение всех своих сессий, кроме текущей
    """
    try:
        await session_service.terminate_other_sessions(current_user.session_id, current_user.user_id)
        return MessageResponse(message="Все остальные сессии успешно завершены")
    
    except Exception as err:
        handle_exception(err, "Ошибка при завершении не текущих сессий", status.HTTP_500_INTERNAL_SERVER_ERROR)

@session_router.delete(
    "/{session_id}",
    response_model=MessageResponse,
    summary="Завершение конкретной сессии"
)
@require_authenticated()
async def deactivate_session(
    request: Request,
    session_id: str,
    current_user: TokenPayload = Depends(get_current_user_payload),
    session_service: SessionService = Depends(create_session_service),
) -> MessageResponse:
    """ 
    Авторизованный API. Доступ: `Администраторы`, `Создатель сессии`\n 
    Завершение конкретной сессии пользователя по ID сессии
    """
    try:
        await session_service.deactivate_session(session_id, current_user.user_id, current_user.role)
        return MessageResponse(message="Сессия успешно завершена")
    
    except Exception as err:
        handle_exception(err, "Ошибка при завершении сессии", status.HTTP_500_INTERNAL_SERVER_ERROR)
