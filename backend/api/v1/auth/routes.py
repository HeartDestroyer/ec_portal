# backend/api/auth/routes.py

from fastapi import APIRouter, Depends, Response, Request, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import Dict, Any, Optional, List
from core.extensions.logger import logger
import uuid

# Схемы
from .schemas import (
    UserCreate, UserLogin, UserPrivateProfile, MessageResponse, RequestPasswordReset, 
    ResetPassword, CSRFTokenResponse, SessionResponse
)

# Сервисы и зависимости
from .services import AuthenticationService, SessionService
from api.v1.dependencies import (
    get_db, get_redis, get_current_active_user, settings, get_current_user_payload
)
from core.models.user import User
from core.security.jwt import JWTHandler
from core.security.csrf import CSRFProtection
from core.security.email import email_manager

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Аутентификация и авторизация"])

# Регистрация пользователя
@auth_router.post(
    "/register", 
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя"
)
async def register_user_endpoint(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Регистрирует нового пользователя в системе.
    Требует уникальные `login` и `email`.
    Валидирует `password` на сложность.
    Отправляет письмо для подтверждения и активации аккаунта.
    """
    jwt_handler = JWTHandler(settings)
    auth_service = AuthenticationService(db, redis, jwt_handler, email_manager)
    try:
        new_user, message = await auth_service.register(user_data)
        return {"user": new_user.to_public_dict(), "message": message}
    
    except HTTPException as err:
        raise err
    except Exception as err:
        logger.error(f"Неожиданная ошибка при регистрации пользователя: {err}")
        raise HTTPException(status_code=500, detail="Ошибка регистрации пользователя")

# Вход в систему
@auth_router.post(
    "/login", 
    summary="Аутентификация пользователя"
)
async def login_for_access_token(
    response: Response,
    request: Request,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Аутентифицирует пользователя по `login`/ `email` и `password`.
    Устанавливает `refresh_token` и `access_token` в HttpOnly cookie.
    Реализована защита от брутфорса.
    Создает сессию для пользователя в таблице `sessions`.
    """
    jwt_handler = JWTHandler(settings)
    auth_service = AuthenticationService(db, redis, jwt_handler, email_manager)

    try:
        access_token, refresh_token = await auth_service.authenticate_user(credentials, request)
        await jwt_handler.set_refresh_token_cookie(response, refresh_token)
        await jwt_handler.set_access_token_cookie(response, access_token)

        return {"message": "Успешный вход"}
    
    except HTTPException as err:
        raise err
    except Exception as err:
        logger.error(f"Неожиданная ошибка при входе: {err}")
        raise HTTPException(status_code=500, detail="Ошибка входа на портал")

# Обновление токенов
@auth_router.post(
    "/refresh", 
    summary="Обновление токенов"
)
async def refresh_tokens_endpoint(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Обновляет `access` и `refresh` токены, используя `refresh` токен из HttpOnly cookie
    Устанавливает новый `refresh_token` и `access_token` в HttpOnly cookie.
    Если пользователь неактивен или не существует, токены аннулируются.
    Если сессия невалидна, токены аннулируются.
    """
    refresh_token = request.cookies.get(JWTHandler(settings).refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh токен отсутствует"
        )
    
    jwt_handler = JWTHandler(settings)
    auth_service = AuthenticationService(db, redis, jwt_handler, email_manager)

    try:
        new_access_token, new_refresh_token = await auth_service.refresh_access_token(refresh_token)

        # Установка нового refresh и access токенов в куки
        await jwt_handler.set_refresh_token_cookie(response, new_refresh_token)
        await jwt_handler.set_access_token_cookie(response, new_access_token)

        return {"message": "Токены обновлены"}
    
    except HTTPException as err:
        if err.status_code == status.HTTP_401_UNAUTHORIZED:
             response.delete_cookie(
                key=jwt_handler.refresh_cookie_name,
                path="/api",
                secure=settings.SESSION_COOKIE_SECURE if hasattr(settings, 'SESSION_COOKIE_SECURE') else True,
                httponly=True,
                samesite="lax"
            )
        raise err
    
    except Exception as err:
        logger.error(f"Неожиданная ошибка при обновлении токена: {err}")
        raise HTTPException(status_code=500, detail="Ошибка обновления токена")

# Выход из системы
@auth_router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Выход из системы"
)
async def logout_endpoint(
    response: Response,
    redis: Redis = Depends(get_redis),
    # Пытаемся получить payload, но не выбрасываем ошибку, если токен невалиден
    payload: Optional[Dict[str, Any]] = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
):
    """
    Выход из системы.
    Отзывает токены в Redis.
    Удаляет `refresh` и `access` токены из куки и завершает сессию.
    """
    jwt_handler = JWTHandler(settings)
    auth_service = AuthenticationService(db, redis, jwt_handler, email_manager)
    
    try:
        user_id, session_id = await auth_service.logout(payload)
        logger.info(f"Токены в контексте сессии {session_id} аннулированы для пользователя {user_id}")

    except HTTPException as err:
        raise err
    except Exception as err:
        logger.error(f"Неожиданная ошибка при выходе из системы: {err}")
        raise HTTPException(status_code=500, detail="Ошибка выхода из системы")

    # Удаление куки в любом случае
    response.delete_cookie(
        key=jwt_handler.refresh_cookie_name,
        path="/api",
        secure=settings.SESSION_COOKIE_SECURE if hasattr(settings, 'SESSION_COOKIE_SECURE') else True,
        httponly=True,
        samesite="lax"
    )

    response.delete_cookie(
        key=jwt_handler.access_cookie_name,
        path="/api",
        secure=settings.SESSION_COOKIE_SECURE if hasattr(settings, 'SESSION_COOKIE_SECURE') else True,
        httponly=True,
        samesite="lax"
    )
    
    return MessageResponse(message="Успешный выход")

# Получение текущего пользователя
@auth_router.get(
    "/me", 
    response_model=UserPrivateProfile, 
    summary="Получение данных текущего пользователя"
)
async def read_users_me(
    current_user: User = Depends(get_current_active_user) # Зависимость проверяет токен и активность
):
    """
    Возвращает информацию о текущем аутентифицированном пользователе
    Требует валидный `access_token` в заголовке `Authorization: Bearer <token>`
    """
    return current_user

# Запрос на сброс пароля
@auth_router.post(
    "/request-password-reset",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Запрос на сброс пароля"
)
async def request_password_reset_endpoint(
    data: RequestPasswordReset,
    db: AsyncSession = Depends(get_db)
):
    """
    Отправляет ссылку для сброса пароля на указанный `email`, если пользователь существует.
    Всегда возвращает успешный ответ, чтобы не раскрывать существование email.
    """
    if not email_manager:
        raise HTTPException(status_code=503, detail="Сервис email временно недоступен")

    # Используем None для Redis и JWT, т.к. они не нужны здесь
    auth_service = AuthenticationService(db, None, None, email_manager)
    await auth_service.request_password_reset_service(data.email)
    return MessageResponse(message="Если почта зарегистрирована, ссылка для сброса пароля будет отправлена")

# Сброс пароля
@auth_router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Установка нового пароля"
)
async def reset_password_endpoint(
    data: ResetPassword,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Устанавливает новый пароль, используя `токен` из `email`
    Валидирует новый пароль и отзывает все активные сессии пользователя
    """
    if not email_manager:
        raise HTTPException(status_code=503, detail="Сервис email временно недоступен")

    jwt_handler = JWTHandler(settings)
    auth_service = AuthenticationService(db, redis, jwt_handler, email_manager)
    
    try:
        await auth_service.reset_password_service(data)
        return MessageResponse(message="Пароль успешно сброшен")
    except HTTPException as err:
        raise err
    except Exception as err:
        logger.error(f"Непредвиденная ошибка при сбросе пароля: {err}")
        raise HTTPException(status_code=500, detail="Ошибка сброса пароля")

# Верификация email
@auth_router.get(
    "/verify-email",
    response_model=MessageResponse,
    summary="Подтверждение email"
)
async def verify_email_endpoint(
    token: str = Query(..., description="Токен подтверждения email"),
    db: AsyncSession = Depends(get_db),
):
    """
    Подтверждает `email` пользователя, используя `token` из ссылки
    Активирует аккаунт пользователя
    """
    if not email_manager:
        raise HTTPException(status_code=503, detail="Сервис email временно недоступен")

    auth_service = AuthenticationService(db, None, None, email_manager)
    
    try:
        await auth_service.verify_email_token(token)
        return MessageResponse(message="Почта успешно подтверждена")
    except HTTPException as err:
        raise HTTPException(status_code=500, detail="Ошибка подтверждения почты")
    except Exception as err:
        logger.error(f"Непредвиденная ошибка при подтверждении email: {err}")
        raise HTTPException(status_code=500, detail="Ошибка подтверждения почты")

# Отправка повторной верификации email
@auth_router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Повторная отправка письма для подтверждения email"
)
async def resend_verification_email_endpoint(
    current_user: User = Depends(get_current_active_user) # Требуется аутентификация
):
    """
    Повторно отправляет письмо для подтверждения `email` текущего пользователя
    Доступно только для пользователей, чей `email` еще не подтвержден
    """
    if not email_manager:
         raise HTTPException(status_code=503, detail="Сервис email временно недоступен")

    # Используем None для Redis и JWT
    auth_service = AuthenticationService(None, None, None, email_manager)
    try:
        await auth_service.request_email_verification(current_user)
        return MessageResponse(message="Письмо для подтверждения отправлено.")
    except HTTPException as err:
        raise err
    except Exception as err:
        logger.error(f"Непредвиденная ошибка при повторной отправке письма для подтверждения email: {err}")
        raise HTTPException(status_code=500, detail="Ошибка отправки письма")

# Для получения CSRF токена
@auth_router.get(
    "/csrf",
    response_model=CSRFTokenResponse,
    summary="Получение CSRF токена"
)
async def get_csrf_token(response: Response):
    """
    Генерирует `CSRF токен` и устанавливает его в куки (не HttpOnly)
    Фронтенд должен будет прочитать эту куку и добавить значение в заголовок `X-CSRF-Token`
    """
    csrf_handler = CSRFProtection(settings)
    csrf_token = csrf_handler.generate_token()
    await csrf_handler.set_csrf_token_cookie(response, csrf_token)
    return CSRFTokenResponse(csrf_token=csrf_token)

# Получение активных сессий
@auth_router.get(
    "/sessions",
    response_model=List[SessionResponse],
    summary="Получение списка активных сессий пользователя"
)
async def get_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """
    Получение списка активных сессий пользователя\n
    Требуется валидный `refresh_token` в куки
    """
    jwt_handler = JWTHandler(settings)
    refresh_token = request.cookies.get(jwt_handler.refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh токен отсутствует"
        )

    try:
        payload = await jwt_handler.verify_token(refresh_token, "refresh", redis)
        user_id = payload.get("id")
        session_id = payload.get("session_id")

        if not user_id or not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный refresh токен"
            )

        # Проверяем валидность сессии
        session_service = SessionService(db, jwt_handler)
        if not await session_service.check_session_validity(str(session_id)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Сессия истекла или неактивна"
            )

        sessions = await session_service.get_user_sessions(user_id, session_id)
        return sessions

    except HTTPException as err:
        raise err
    except Exception as err:
        logger.error(f"Ошибка при получении списка сессий: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении списка сессий"
        )

# Завершение конкретной сессии
@auth_router.delete(
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
    Требуется валидный `refresh_token` в куки
    """
    try:
        # Проверяем, что session_id является валидным UUID
        uuid.UUID(session_id)
        
        jwt_handler = JWTHandler(settings)
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

        # Деактивируем указанную сессию
        await session_service.deactivate_session(session_id, user_id)
        return MessageResponse(message="Сессия успешно завершена")

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
@auth_router.delete(
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
    jwt_handler = JWTHandler(settings)
    refresh_token = request.cookies.get(jwt_handler.refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh токен отсутствует"
        )

    try:
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
