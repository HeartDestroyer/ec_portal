import pytest
from core.security.password import password_manager
from core.models.user import User

@pytest.mark.asyncio
async def test_password_hashing():
    """Тест хеширования пароля"""
    password = "testTest123!"
    hashed = password_manager.hash_password(password)
    
    assert hashed != password
    assert password_manager.verify_password(password, hashed)
    assert not password_manager.verify_password("wrong_password", hashed)

@pytest.mark.asyncio
async def test_user_creation(test_db, test_user_data):
    """Тест создания пользователя"""
    session = await anext(test_db)  # Получаем сессию из генератора
    
    user = User(
        login=test_user_data["login"],
        email=test_user_data["email"],
        hashed_password=password_manager.hash_password(test_user_data["password"]),
        name=test_user_data["name"],
        phone=test_user_data["phone"]
    )
    
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    assert user.id is not None
    assert user.login == test_user_data["login"]
    