from fastapi import APIRouter, Depends, Response, Request, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import Optional

from api.v1.schemas import MessageResponse, TokenPayload
from api.v1.dependencies import (
    JWTHandler, CSRFProtection, EmailManager, SessionManager,
    get_db, get_redis, settings, logger, jwt_handler, email_manager,
    require_admin_roles, require_not_guest, require_authenticated,
    handle_exception,
    get_refresh_token_from_request, get_access_token_from_request,
    get_current_user_payload, get_current_active_user
)
from .schemas import UserCreate, UserLogin, RequestPasswordReset, ResetPassword, UserPublicProfile, UserPrivateProfile, CSRFTokenResponse
from .services import AuthenticationService

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Аутентификация и авторизация"])

def create_auth_service(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    jwt_handler: Optional[JWTHandler] = Depends(JWTHandler),
    email_manager: Optional[EmailManager] = Depends(EmailManager),
) -> AuthenticationService:
    """
    Создает экземпляр сервиса аутентификации
    """
    return AuthenticationService(db, redis, jwt_handler, email_manager)

def delete_auth_cookies(
    response: Response, 
    jwt_handler: JWTHandler
) -> None:
    """
    Удаляет куки аутентификации из cookies
    """
    cookie_settings = {
        "path": "/api",
        "secure": settings.SESSION_COOKIE_SECURE if hasattr(settings, 'SESSION_COOKIE_SECURE') else True,
        "httponly": True,
        "samesite": "lax"
    }

    response.delete_cookie(key=jwt_handler.refresh_cookie_name, **cookie_settings)
    response.delete_cookie(key=jwt_handler.access_cookie_name, **cookie_settings)

@auth_router.post(
    "/register", 
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя"
)
async def register_user_endpoint(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    jwt_handler: JWTHandler = Depends(JWTHandler),
    email_manager: EmailManager = Depends(EmailManager),
) -> MessageResponse:
    """
    Регистрирует нового пользователя в системе\n
    Требует уникальные `login` и `email` и валидирует `password` на сложность\n
    Отправляет письмо для подтверждения и активации аккаунта
    """
    auth_service = create_auth_service(db, redis, jwt_handler, email_manager)
    try:
        user = await auth_service.register_service(user_data)
        return MessageResponse(message=f"Письмо для подтверждения отправлено на почту {user.email}")
    
    except HTTPException as err:
        raise err
    except Exception as err:
        logger.error(f"Ошибка при регистрации пользователя: {err}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Неожиданная ошибка при регистрации пользователя")

@auth_router.post(
    "/login", 
    response_model=MessageResponse,
    summary="Аутентификация пользователя"
)
async def login_for_access_token(
    response: Response,
    request: Request,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    jwt_handler: JWTHandler = Depends(JWTHandler),
    email_manager: EmailManager = Depends(EmailManager),
) -> MessageResponse:
    """
    Аутентифицирует пользователя по `login`/`email` и password\n
    Устанавливает `refresh_token` и `access_token` в HttpOnly cookie\n
    Реализована защита от брутфорса\n
    Создает сессию для пользователя в таблице Sessions
    """
    auth_service = create_auth_service(db, redis, jwt_handler, email_manager)
    try:
        tokens = await auth_service.authenticate_user_service(credentials, request)
        await jwt_handler.set_token_cookie(response, tokens.refresh_token, jwt_handler.refresh_cookie_name)
        await jwt_handler.set_token_cookie(response, tokens.access_token, jwt_handler.access_cookie_name)
        return MessageResponse(message="Добро пожаловать на портал")
    
    except HTTPException as err:
        raise err
    except Exception as err:
        logger.error(f"Ошибка при входе: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Неожиданная ошибка при входе"
        )

@auth_router.post(
    "/refresh", 
    response_model=None,
    summary="Обновление токенов"
)
async def refresh_tokens(
    request: Request, 
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    jwt_handler: JWTHandler = Depends(JWTHandler),
) -> None:
    """
    Обновление токенов аутентифицированного пользователя\n
    Токен обновления берется из cookie\n
    В ответе обновленные токены в виде cookie
    """
    try:
        refresh_token = await get_refresh_token_from_request(request)
        auth_service = create_auth_service(db, redis, jwt_handler)
        try:
            await jwt_handler.verify_token(refresh_token, "refresh", redis)
        except HTTPException as err:
            delete_auth_cookies(response, jwt_handler)
            raise
        
        tokens = await auth_service.refresh_tokens_service(refresh_token)
        await jwt_handler.set_token_cookie(response, tokens.refresh_token, jwt_handler.refresh_cookie_name)
        await jwt_handler.set_token_cookie(response, tokens.access_token, jwt_handler.access_cookie_name)
                
    except HTTPException:
        delete_auth_cookies(response, jwt_handler)
        raise
    except Exception as err:
        delete_auth_cookies(response, jwt_handler)
        raise handle_exception(err, "Неожиданная ошибка при обновлении токена")

@auth_router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Выход из системы"
)
@require_authenticated()
async def logout_endpoint(
    request: Request,
    response: Response,
    redis: Redis = Depends(get_redis),
    jwt_handler: JWTHandler = Depends(JWTHandler),
    token_payload: TokenPayload = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Авторизованный API. Доступ: `Авторизованные пользователи`\n
    Выход из системы и отзыв токенов\n
    Удаляет токены из куки и завершает сессию
    """
    auth_service = create_auth_service(db, redis, jwt_handler)
    try:
        refresh_token = await get_refresh_token_from_request(request)
        await auth_service.logout_service(token_payload.user_id, token_payload.session_id, refresh_token)
        delete_auth_cookies(response, jwt_handler)
        return MessageResponse(message="Вы успешно вышли из системы")
    
    except HTTPException as err:
        raise err
    except Exception as err:
        logger.error(f"Ошибка при выходе из системы: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Неожиданная ошибка при выходе из системы"
        )

@auth_router.get(
    "/me", 
    response_model=UserPrivateProfile, 
    summary="Получение данных текущего пользователя"
)
@require_authenticated()
async def read_users_me(
    request: Request,
    db: AsyncSession = Depends(get_db),
    token_payload: TokenPayload = Depends(get_current_user_payload),
) -> UserPrivateProfile:
    """
    Авторизованный API. Доступ: `Авторизованные пользователи`\n
    Возвращает информацию о текущем аутентифицированном пользователе
    """
    try:
        user = await get_current_active_user(token_payload, db)
        return UserPrivateProfile.model_validate(user)
    
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Ошибка при получении данных пользователя: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Неожиданная ошибка при получении данных пользователя"
        )

@auth_router.post(
    "/request-password-reset",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Запрос на сброс пароля"
)
async def request_password_reset_endpoint(
    data: RequestPasswordReset,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Отправляет ссылку для сброса пароля на указанную почту, если пользователь существует\n
    Всегда возвращает успешный ответ, чтобы не раскрывать существование почты
    """
    auth_service = create_auth_service(db, None)
    return await auth_service.request_password_reset_service(data.email)

@auth_router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Установка нового пароля"
)
async def reset_password_endpoint(
    data: ResetPassword,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> MessageResponse:
    """
    Устанавливает новый пароль, используя токен из письма\n
    Валидирует новый пароль и отзывает все активные сессии пользователя
    """
    auth_service = create_auth_service(db, redis)
    return await auth_service.reset_password_service(data)
    
@auth_router.get(
    "/verify-email",
    response_model=MessageResponse,
    summary="Подтверждение email"
)
async def verify_email_endpoint(
    token: str = Query(..., description="Токен подтверждения почты"),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Подтверждает почту пользователя по токену из письма\n
    Активирует аккаунт пользователя
    """
    auth_service = create_auth_service(db, None)
    return await auth_service.verify_email_service(token)

@auth_router.get(
    "/csrf",
    response_model=CSRFTokenResponse,
    summary="Получение CSRF токена"
)
@require_authenticated()
async def get_csrf_token(
    request: Request,
    response: Response,
    csrf_protection: CSRFProtection = Depends(CSRFProtection),
) -> CSRFTokenResponse:
    """
    Авторизованный API. Доступ: `Авторизованные пользователи`\n
    Получение CSRF токена для защиты от CSRF атак\n
    Возвращает CSRF токен, который нужно добавить в заголовок X-XSRF-TOKEN для защищенных запросов
    """
    try:        
        csrf_token = csrf_protection.generate_csrf_token()
        await csrf_protection.set_csrf_token_cookie(response, csrf_token)
        return CSRFTokenResponse(csrf_token=csrf_token)
        
    except Exception as err:
        logger.error(f"Ошибка при получении CSRF токена: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении CSRF токена"
        )

@auth_router.post(
    "/2fa",
    response_model=MessageResponse,
    summary="Включение двухфакторной аутентификации"
)
@require_authenticated()
async def enable_2fa_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Авторизованный API. Доступ: `Авторизованные пользователи`\n
    Включает двухфакторную аутентификацию для текущего пользователя
    """
    try:      
        auth_service = create_auth_service(db, None)
        return await auth_service.enable_2fa_service()
    
    except HTTPException as err:
        raise err
    except Exception as err:
        logger.error(f"Ошибка при включении двухфакторной аутентификации: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Неожиданная ошибка при включении двухфакторной аутентификации"
        )

