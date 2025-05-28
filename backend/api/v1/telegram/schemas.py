from pydantic import BaseModel, HttpUrl, field_validator, Field
from typing import Optional, List
from datetime import datetime

from models.telegram import RuleType, City, Gender

# Схема базового правила для ТГ группы
class ChannelRuleBase(BaseModel):
    rule_type: str = Field(..., description="Тип правила")
    city: Optional[str] = Field(None, description="Город")
    gender: Optional[str] = Field(None, description="Пол")
    department_id: Optional[str] = Field(None, description="ID отдела")
    group_id: Optional[str] = Field(None, description="ID группы")
    channel_name: str = Field(..., description="Название группы")
    channel_url: Optional[HttpUrl] = Field(None, description="URL группы")
    chat_id: Optional[int] = Field(None, description="ID чата")
    user_ids: Optional[List[str]] = Field(None, description="ID пользователей")

# Схема создания правила для ТГ группы
class ChannelRuleCreate(ChannelRuleBase):
    @field_validator('rule_type')
    def validate_rule_type(cls, v):
        valid_types = [e.value for e in RuleType]
        if v not in valid_types:
            raise ValueError(f"rule_type должен быть одним из: {valid_types}")
        return v
    
    @field_validator('city')
    def validate_city(cls, v):
        if v and v not in [e.value for e in City]:
            raise ValueError(f"city должен быть одним из: {[e.value for e in City]}")
        return v

    @field_validator('gender')
    def validate_gender(cls, v):
        if v and v not in [e.value for e in Gender]:
            raise ValueError(f"gender должен быть одним из: {[e.value for e in Gender]}")
        return v
    
    @field_validator('channel_url')
    def validate_channel_url(cls, v):
        if v and not v.startswith("https://t.me/"):
            raise ValueError("channel_url должен начинаться с https://t.me/")
        return v

# Схема ответа на запрос на получение правила для ТГ группы
class ChannelRuleResponse(ChannelRuleBase):
    id: str = Field(..., description="ID правила")
    channel_url: HttpUrl = Field(..., description="URL группы")
    channel_name: str = Field(..., description="Название группы")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    class Config:
        from_attributes = True
