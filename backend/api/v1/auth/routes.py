# backend/api/auth/routes.py

from fastapi import APIRouter, Depends, Response, Request, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from aioredis import Redis

# Схемы
from .schemas import (
    UserCreate, UserLogin, TokenResponse, UserPublicProfile,
    UserPrivateProfile, MessageResponse, RequestPasswordReset, ResetPassword,
    CSRFTokenResponse
)
# Сервисы
from .services import AuthenticationService
# Зависимости
from api.v1.dependencies import (
    get_db, get_redis, get_settings, Settings, get_current_active_user,
    csrf_verify_header # Если используем CSRF
)
from core.models.user import User
from core.security.jwt import JWTHandler
from core.security.csrf import CSRFProtection
from core.security.email import EmailManager

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# Регистрация пользователя
@auth_router.post(
    "/register", 
    response_model=UserPublicProfile, 
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя"
)
async def register_user_endpoint(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings)
):
    """
    Регистрирует нового пользователя в системе
    Требует уникальные `username` и `email`
    Валидирует пароль на сложность
    Отправляет письмо для подтверждения email
    """
    jwt_handler = JWTHandler(settings)
    auth_service = AuthenticationService(db, redis, jwt_handler, email_manager)
    try:
        new_user = await auth_service.register_user(user_data)
        return new_user
    except HTTPException as err:
        raise err # Пробрасываем ошибки валидации и существования пользователя
    except Exception as err:
         # Логгирование непредвиденной ошибки
         print(f"Неожиданная ошибка при регистрации: {err}")
         raise HTTPException(status_code=500, detail="Ошибка регистрации")
    
# Вход в систему
@auth_router.post(
    "/login", 
    response_model=TokenResponse, 
    summary="Аутентификация пользователя"
)
async def login_for_access_token(
    response: Response, # Для установки куки
    credentials: UserLogin = Depends(), # Используем Depends для данных формы
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings)
):
    """
    Аутентифицирует пользователя по имени/email и паролю
    Возвращает `access_token`
    Устанавливает `refresh_token` в HttpOnly cookie
    Реализована защита от брутфорса
    """
    jwt_handler = JWTHandler(settings)
    auth_service = AuthenticationService(db, redis, jwt_handler)

    try:
        user, access_token, refresh_token = await auth_service.authenticate_user(
            credentials.username_or_email,
            credentials.password
        )
        # Установка refresh токена в куки
        await jwt_handler.set_refresh_token_cookie(response, refresh_token)
        return TokenResponse(access_token=access_token)
    except HTTPException as err:
        raise err
    except Exception as err:
         print(f"Неожиданная ошибка при входе: {err}")
         raise HTTPException(status_code=500, detail="Ошибка входа")

# Обновление токенов
@auth_router.post(
    "/refresh", 
    response_model=TokenResponse,
    summary="Обновление токенов"
)
async def refresh_tokens_endpoint(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings)
):
    """
    бновляет access и refresh токены, используя refresh токен из HttpOnly cookie
    Возвращает `access_token`
    Устанавливает новый `refresh_token` в HttpOnly cookie
    """
    refresh_token = request.cookies.get(JWTHandler(settings).refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh токен отсутствует"
        )
    
    jwt_handler = JWTHandler(settings)
    auth_service = AuthenticationService(db, redis, jwt_handler)

    try:
        new_access_token, new_refresh_token = await auth_service.refresh_access_token(refresh_token)
        # Установка нового refresh токена в куки
        await jwt_handler.set_refresh_token_cookie(response, new_refresh_token)
        return TokenResponse(access_token=new_access_token)
    except HTTPException as err:
        # Если токен невалиден или отозван, удаляем куку
        if err.status_code == status.HTTP_401_UNAUTHORIZED:
             response.delete_cookie(
                key=jwt_handler.refresh_cookie_name,
                path="/api/v1/auth",
                secure=settings.SESSION_COOKIE_SECURE if hasattr(settings, 'SESSION_COOKIE_SECURE') else True,
                httponly=True,
                samesite="lax"
            )
        raise err
    
    except Exception as err:
         print(f"Неожиданная ошибка при обновлении токена: {err}")
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
    settings: Settings = Depends(get_settings),
    # Пытаемся получить payload, но не выбрасываем ошибку, если токен невалиден
    payload: Optional[Dict[str, Any]] = Depends(get_current_user_payload)
):
    """
    Выход из системы
    Отзывает токены в Redis
    Удаляет refresh токен из куки
    """
    jwt_handler = JWTHandler(settings)
    user_id = payload.get("sub") if payload else None
    
    if user_id:
        await jwt_handler.revoke_tokens(user_id, redis)
        print(f"Токены аннулированы для пользователя {user_id}")

    # Удаление куки в любом случае
    response.delete_cookie(
        key=jwt_handler.refresh_cookie_name,
        path="/api/v1/auth",
        secure=settings.SESSION_COOKIE_SECURE if hasattr(settings, 'SESSION_COOKIE_SECURE') else True,
        httponly=True,
        samesite="lax"
    )
    print("Refresh токен удален")
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
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    """
    Отправляет ссылку для сброса пароля на указанный email, если пользователь существует.
    Всегда возвращает успешный ответ, чтобы не раскрывать существование email.
    """
    if not email_manager:
         raise HTTPException(status_code=503, detail="Сервис email временно недоступен")

    # Используем None для Redis и JWT, т.к. они не нужны здесь
    auth_service = AuthenticationService(db, None, None, email_manager)
    await auth_service.request_password_reset_service(data.email)
    return MessageResponse(message="Если email зарегистрирован, ссылка для сброса пароля отправлена")

# Сброс пароля
@auth_router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Установка нового пароля"
)
async def reset_password_endpoint(
    data: ResetPassword,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings)
):
    """
    Устанавливает новый пароль, используя токен из email
    Валидирует новый пароль и отзывает все активные сессии пользователя
    """
    if not email_manager:
        raise HTTPException(status_code=503, detail="Сервис email временно недоступен")

    jwt_handler = JWTHandler(settings)
    # Нужен Redis для отзыва токенов
    auth_service = AuthenticationService(db, redis, jwt_handler, email_manager)
    try:
        await auth_service.reset_password_service(data)
        return MessageResponse(message="Пароль успешно сброшен")
    except HTTPException as err:
        raise err
    except Exception as err:
        print(f"Непредвиденная ошибка при сбросе пароля: {err}")
        raise HTTPException(status_code=500, detail="Ошибка сброса пароля")

# Верификация email
@auth_router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Подтверждение email"
)
async def verify_email_endpoint(
    token: str = Body(..., embed=True), # Получаем токен из тела запроса
    db: AsyncSession = Depends(get_db),
):
    """
    Подтверждает email пользователя, используя токен из ссылки
    Активирует аккаунт пользователя
    """
    if not email_manager:
         raise HTTPException(status_code=503, detail="Сервис email временно недоступен")

    # Используем None для Redis и JWT
    auth_service = AuthenticationService(db, None, None, email_manager)
    try:
        await auth_service.verify_email_token(token)
        return MessageResponse(message="email успешно подтвержден")
    except HTTPException as err:
        raise err
    except Exception as err:
         print(f"Непредвиденная ошибка при подтверждении email: {err}")
         raise HTTPException(status_code=500, detail="Ошибка подтверждения email")

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
    Повторно отправляет письмо для подтверждения email текущего пользователя
    Доступно только для пользователей, чей email еще не подтвержден
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
         print(f"Непредвиденная ошибка при повторной отправке письма для подтверждения email: {err}")
         raise HTTPException(status_code=500, detail="Ошибка отправки письма")

# Для получения CSRF токена (если используется Double Submit Cookie)
@auth_router.get(
    "/csrf-token",
    response_model=CSRFTokenResponse,
    summary="Получение CSRF токена"
)
async def get_csrf_token(response: Response, settings: Settings = Depends(get_settings)):
    """
    Генерирует CSRF токен и устанавливает его в куки (не HttpOnly)
    Фронтенд должен будет прочитать эту куку и добавить значение в заголовок X-CSRF-Token
    """
    csrf_handler = CSRFProtection(settings)
    csrf_token = csrf_handler.generate_token()
    response.set_cookie(
        key="csrf_token", # Имя куки должно совпадать с тем, что проверяется
        value=csrf_token,
        secure=settings.SESSION_COOKIE_SECURE if hasattr(settings, 'SESSION_COOKIE_SECURE') else True,
        samesite="lax",
        httponly=False # Важно: False, чтобы JS мог прочитать
    )
    return CSRFTokenResponse(csrf_token=csrf_token)

# Подключаем роутер авторизации к основному приложению в main.py
app.include_router(auth_router)