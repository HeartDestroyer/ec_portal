from fastapi import APIRouter

from .auth.routes import auth_router
from .cache.routes import cache_router
from .session.routes import session_router
from .user.routes import user_router
from .telegram.routes import telegram_router

api_router = APIRouter()

api_router.include_router(auth_router) # Роутер для аутентификации
api_router.include_router(cache_router) # Роутер для кэширования
api_router.include_router(session_router) # Роутер для сессий пользователей
api_router.include_router(user_router) # Роутер для управления пользователями
api_router.include_router(telegram_router) # Роутер для управления ТГ-группами
