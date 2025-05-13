from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime

class SessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_name: Optional[str] = None
    device: Optional[str] = None
    browser: Optional[str] = None
    os: Optional[str] = None
    platform: Optional[str] = None
    location: Optional[str] = None
    ip_address: Optional[str] = None
    last_activity: datetime
    created_at: datetime
    is_active: bool
    is_current: bool = False

    class Config:
        from_attributes = True

class SessionFilter(BaseModel):
    user_id: Optional[uuid.UUID] = None
    user_name: Optional[str] = None
    is_active: Optional[bool] = None
    page: int = 1
    page_size: int = 20

class SessionsPage(BaseModel):
    total: int
    page: int
    page_size: int
    sessions: List[SessionResponse]

class MessageResponse(BaseModel):
    message: str
