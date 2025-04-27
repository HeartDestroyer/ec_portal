import pytest
from core.security.email import email_manager
from datetime import timedelta

@pytest.fixture
def email_manager():
    return email_manager

@pytest.mark.asyncio
async def test_create_verification_token(email_manager):
    """Тест создания токена верификации"""
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    token = email_manager._create_token(
        {"sub": user_id, "type": "email_verification"},
        expires_delta=timedelta(hours=24)
    )
    
    assert token is not None
    decoded = email_manager.verify_token(token, "email_verification")
    assert decoded is not None
    assert decoded["sub"] == user_id

@pytest.mark.asyncio
async def test_verify_invalid_token(email_manager):
    """Тест проверки невалидного токена"""
    result = email_manager.verify_token("invalid_token", "email_verification")
    assert result is None