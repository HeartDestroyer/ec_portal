from pydantic import BaseModel
from typing import List

# Схема для получения информации о Redis
class RedisInfo(BaseModel):
    memory: dict
    stats: dict
    server: dict
    clients: dict
    persistence: dict

# Схема для получения количества ключей в Redis
class RedisKeys(BaseModel):
    total: int
    pattern: str
    keys: List[str]
