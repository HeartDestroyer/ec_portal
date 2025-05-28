from fastapi import APIRouter, Depends, Request, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import List
from pydantic import BaseModel

from .schemas import ChannelRuleResponse, ChannelRuleCreate
from .services import TelegramService
from api.v1.dependencies import get_current_user_payload, get_db, get_redis, require_admin_roles, jwt_handler
from api.v1.schemas import MessageResponse, TokenPayload
from core.extensions.logger import logger
from models.user import User

telegram_router = APIRouter(prefix="/api/v1/telegram", tags=["Управление ТГ-группами"])

# Создание правила ТГ-чата
@telegram_router.post(
    "/rules",
    response_model=ChannelRuleResponse,
    summary="Создание правила Telegram-чата"
)
@require_admin_roles()
async def create_channel_rule(
    rule_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_roles)
) -> ChannelRuleResponse:
    """
    Создание нового правила для канала
    """
    try:
        service = TelegramService(db)
        result = await service.create_channel_rule(rule_data)
        return result
    except Exception as e:
        logger.error(f"Error creating channel rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании правила канала"
        )

# Обновление правила ТГ-чата
@telegram_router.post(
    "/rules/{rule_id}",
    response_model=ChannelRuleResponse,
    summary="Обновление правила Telegram-чата"
)
@require_admin_roles()
async def update_channel_rule(
    rule_id: str = Path(..., description="ID правила"),
    rule_data: dict = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_roles)
) -> ChannelRuleResponse:
    """
    Обновление правила канала
    """
    try:
        service = TelegramService(db)
        result = await service.update_channel_rule(rule_id, rule_data)
        return result
    except Exception as e:
        logger.error(f"Error updating channel rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении правила канала"
        )

# Удаление правила ТГ-чата
@telegram_router.delete(
    "/rules/{rule_id}",
    response_model=MessageResponse,
    summary="Удаление правила Telegram-чата"
)
@require_admin_roles()
async def delete_channel_rule(
    rule_id: str = Path(..., description="ID правила"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_roles)
) -> MessageResponse:
    """
    Удаление правила канала
    """
    try:
        service = TelegramService(db)
        await service.delete_channel_rule(rule_id)
        return {"message": "Правило успешно удалено"}
    except Exception as e:
        logger.error(f"Error deleting channel rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при удалении правила канала"
        )

# Получение всех правил ТГ-чатов
@telegram_router.get(
    "/rules",
    response_model=List[ChannelRuleResponse],
    summary="Получение всех правил Telegram-чатов"
)
@require_admin_roles()
async def get_all_channel_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_roles)
) -> List[ChannelRuleResponse]:
    """
    Получение всех правил каналов
    """
    try:
        service = TelegramService(db)
        rules = await service.get_all_channel_rules()
        return rules
    except Exception as e:
        logger.error(f"Error getting channel rules: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении правил каналов"
        )
