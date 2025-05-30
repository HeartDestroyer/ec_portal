# backend/api/v1/routes.py - Роуты для API v1

from fastapi import APIRouter

from api.v1.auth.auth_routes import auth_router
from api.v1.cache.routes import cache_router
from backend.api.v1.session.session_routes import session_router
from api.v1.user.routes import user_router
from api.v1.telegram.routes import telegram_router
from api.v1.notifications.routes import notifications_router

api_router = APIRouter()

api_router.include_router(auth_router) # Роутер для аутентификации
api_router.include_router(cache_router) # Роутер для кэширования
api_router.include_router(session_router) # Роутер для сессий пользователей
api_router.include_router(user_router) # Роутер для управления пользователями
api_router.include_router(telegram_router) # Роутер для управления ТГ-группами
api_router.include_router(notifications_router) # Роутер для управления push-уведомлениями
