import pytest
from datetime import datetime, timedelta

@pytest.fixture
def test_users():
    """Тестовые пользователи"""
    return [
        {
            "login": "user1",
            "email": "user1@example.com",
            "password": "Pass123!",
            "name": "User One",
            "phone": "+79991234561"
        },
        {
            "login": "user2",
            "email": "user2@example.com",
            "password": "Pass123!",
            "name": "User Two",
            "phone": "+79991234562"
        }
    ]

@pytest.fixture
def test_tokens():
    """Тестовые токены"""
    return {
        "valid_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "expired_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "invalid_token": "invalid_token"
    }