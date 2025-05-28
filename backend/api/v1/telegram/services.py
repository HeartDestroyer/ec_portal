from datetime import datetime
import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict, Any
import aiohttp
from redis.asyncio import Redis
from enum import Enum

from api.v1.auth.services import AuthenticationService
from api.v1.dependencies import settings
from models.user import User
from models.department import Department
from models.group import Group
from core.extensions.logger import logger
from core.security.jwt import JWTHandler

# Сервис для работы с ТГ группами
class TelegramService:
    """
    Сервис для работы с ТГ группами
    """

    # Инициализация
    def __init__(self, db: AsyncSession, jwt_handler: JWTHandler, redis: Redis):
        self.db = db
        self.jwt_handler = jwt_handler
        self.redis = redis



