import pytest
from fastapi import status

@pytest.mark.asyncio
async def test_register_user(test_client, test_user_data):
    """Тест регистрации пользователя"""
    response = test_client.post(
        "/api/v1/auth/register",
        json=test_user_data
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "id" in data
    assert data["login"] == test_user_data["login"]
    assert data["email"] == test_user_data["email"]

@pytest.mark.asyncio
async def test_login_user(test_client, test_user_data):
    """Тест входа пользователя"""
    response = test_client.post(
        "/api/v1/auth/login",
        json={
            "login_or_email": test_user_data["email"],
            "password": test_user_data["password"]
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_get_current_user(test_client, test_user_data):
    """Тест получения текущего пользователя"""
    # Сначала логинимся
    login_response = test_client.post(
        "/api/v1/auth/login",
        json={
            "login_or_email": test_user_data["email"],
            "password": test_user_data["password"]
        }
    )
    
    token = login_response.json()["access_token"]
    
    # Получаем данные пользователя
    response = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == test_user_data["email"]
    assert data["login"] == test_user_data["login"]
