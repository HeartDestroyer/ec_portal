# Роутеры
from fastapi import APIRouter

# Роутеры
from .auth.routes import auth_router
from .cache.routes import cache_router

api_router = APIRouter()

# Подключаем роутеры
api_router.include_router(auth_router)
api_router.include_router(cache_router)
