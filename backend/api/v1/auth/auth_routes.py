# backend/api/v1/auth/routes_auth.py - Роуты для аутентификации и авторизации

from fastapi import APIRouter, Depends, Response, Request, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.schemas import MessageResponse, TokenPayload
from api.v1.dependencies import (
    CSRFProtection, get_db, settings, require_authenticated, handle_exception,
    get_refresh_token_from_request, get_current_user_payload, get_current_active_user
)
from api.v1.auth.schemas import (
    UserCreate, UserLogin, RequestPasswordReset, ResetPassword, UserPrivateProfile, CSRFTokenResponse
)
from api.v1.auth.services import (
    AuthenticationService, RegistrationService, PasswordService, TwoFactorService
)
from api.v1.auth.dependencies import (
    create_authentication_service, create_registration_service, create_password_service, create_two_factor_service
)

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Аутентификация и авторизация"])

def delete_auth_cookies(response: Response, access_cookie_name: str, refresh_cookie_name: str) -> None:
    """
    Удаляет куки аутентификации из cookies\n
    `access_cookie_name` - Имя куки для access токена\n
    `refresh_cookie_name` - Имя куки для refresh токена
    """
    cookie_settings = {
        "path": "/api",
        "secure": settings.SESSION_COOKIE_SECURE if hasattr(settings, 'SESSION_COOKIE_SECURE') else True,
        "httponly": True,
        "samesite": "lax"
    }

    response.delete_cookie(key=access_cookie_name, **cookie_settings)
    response.delete_cookie(key=refresh_cookie_name, **cookie_settings)

@auth_router.post(
    "/register", 
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя"
)
async def register_user_endpoint(
    user_data: UserCreate,
    registration_service: RegistrationService = Depends(create_registration_service)
) -> MessageResponse:
    """
    Регистрирует нового пользователя в системе\n
    Требует уникальные `login` и `email` и валидирует `password` на сложность\n
    Отправляет письмо для подтверждения и активации аккаунта
    """
    try:
        user = await registration_service.register_service(user_data)
        return MessageResponse(message=f"Письмо для подтверждения отправлено на почту {user.email}")
    
    except HTTPException as err:
        raise err
    except Exception as err:
        raise handle_exception(err, "Неожиданная ошибка при регистрации пользователя")

@auth_router.post(
    "/login", 
    response_model=MessageResponse,
    summary="Аутентификация пользователя"
)
async def login_for_access_token(
    response: Response,
    request: Request,
    credentials: UserLogin,
    authentication_service: AuthenticationService = Depends(create_authentication_service)
) -> MessageResponse:
    """
    Аутентифицирует пользователя по `login`/`email` и password\n
    Устанавливает `refresh_token` и `access_token` в HttpOnly cookie\n
    Реализована защита от брутфорса\n
    Создает сессию для пользователя в таблице Sessions
    """
    try:
        tokens = await authentication_service.authenticate_user_service(credentials, request)
        await authentication_service.jwt_handler.set_token_cookie(response, tokens.refresh_token, authentication_service.jwt_handler.refresh_cookie_name)
        await authentication_service.jwt_handler.set_token_cookie(response, tokens.access_token, authentication_service.jwt_handler.access_cookie_name)
        return MessageResponse(message="Добро пожаловать на портал")
    
    except HTTPException as err:
        raise err
    except Exception as err:
        raise handle_exception(err, "Неожиданная ошибка при входе")

@auth_router.post(
    "/refresh", 
    response_model=None,
    summary="Обновление токенов"
)
async def refresh_tokens(
    request: Request, 
    response: Response,
    authentication_service: AuthenticationService = Depends(create_authentication_service)
) -> None:
    """
    Обновление токенов аутентифицированного пользователя\n
    Токен обновления берется из cookie\n
    В ответе обновленные токены в виде cookie
    """
    try:
        refresh_token = await get_refresh_token_from_request(request)
        try:
            await authentication_service.jwt_handler.verify_token(refresh_token, "refresh", authentication_service.redis)
        except HTTPException as err:
            delete_auth_cookies(response, authentication_service.jwt_handler)
            raise
        
        tokens = await authentication_service.refresh_tokens_service(refresh_token)
        await authentication_service.jwt_handler.set_token_cookie(response, tokens.refresh_token, authentication_service.jwt_handler.refresh_cookie_name)
        await authentication_service.jwt_handler.set_token_cookie(response, tokens.access_token, authentication_service.jwt_handler.access_cookie_name)
                
    except HTTPException:
        delete_auth_cookies(response, authentication_service.jwt_handler)
        raise
    except Exception as err:
        delete_auth_cookies(response, authentication_service.jwt_handler)
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
    authentication_service: AuthenticationService = Depends(create_authentication_service),
    token_payload: TokenPayload = Depends(get_current_user_payload),
) -> MessageResponse:
    """
    Авторизованный API. Доступ: `Авторизованные пользователи`\n
    Выход из системы и отзыв токенов\n
    Удаляет токены из куки и завершает сессию
    """
    try:
        refresh_token = await get_refresh_token_from_request(request)
        await authentication_service.logout_service(token_payload.user_id, token_payload.session_id, refresh_token)
        delete_auth_cookies(response, authentication_service.jwt_handler)
        return MessageResponse(message="Вы успешно вышли из системы")
    
    except HTTPException as err:
        raise err
    except Exception as err:
        raise handle_exception(err, "Неожиданная ошибка при выходе из системы")

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
        raise handle_exception(err, "Неожиданная ошибка при получении данных пользователя")

@auth_router.post(
    "/request-password-reset",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Запрос на сброс пароля"
)
async def request_password_reset_endpoint(
    data: RequestPasswordReset,
    password_service: PasswordService = Depends(create_password_service),
) -> MessageResponse:
    """
    Отправляет ссылку для сброса пароля на указанную почту, если пользователь существует\n
    Всегда возвращает успешный ответ, чтобы не раскрывать существование почты
    """
    return await password_service.request_password_reset_service(data.email)

@auth_router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Установка нового пароля"
)
async def reset_password_endpoint(
    data: ResetPassword,
    password_service: PasswordService = Depends(create_password_service),
) -> MessageResponse:
    """
    Устанавливает новый пароль, используя токен из письма\n
    Валидирует новый пароль и отзывает все активные сессии пользователя
    """
    return await password_service.reset_password_service(data)
    
@auth_router.get(
    "/verify-email",
    response_model=MessageResponse,
    summary="Подтверждение email"
)
async def verify_email_endpoint(
    token: str = Query(..., description="Токен подтверждения почты"),
    registration_service: RegistrationService = Depends(create_registration_service),
) -> MessageResponse:
    """
    Подтверждает почту пользователя по токену из письма\n
    Активирует аккаунт пользователя
    """
    return await registration_service.verify_email_service(token)

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
        raise handle_exception(err, "Ошибка при получении CSRF токена")

@auth_router.post(
    "/2fa",
    response_model=MessageResponse,
    summary="Включение двухфакторной аутентификации"
)
@require_authenticated()
async def enable_2fa_endpoint(
    request: Request,
    two_factor_service: TwoFactorService = Depends(create_two_factor_service),
) -> MessageResponse:
    """
    Авторизованный API. Доступ: `Авторизованные пользователи`\n
    Включает двухфакторную аутентификацию для текущего пользователя
    """
    try:      
        return await two_factor_service.enable_2fa_service()
    
    except HTTPException as err:
        raise err
    except Exception as err:
        raise handle_exception(err, "Неожиданная ошибка при включении двухфакторной аутентификации")
