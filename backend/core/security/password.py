# backend/core/security/password.py

from passlib.context import CryptContext
import re
from datetime import datetime, timedelta
import random
import string
from core.config.config import settings
# Класс для работы с паролями
class PasswordManager:
    def __init__(self):
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=settings.BCRYPT_ROUNDS
        )
        self.min_length = settings.MIN_LENGTH
        self.max_failed_attempts = settings.MAX_FAILED_ATTEMPTS
        self.lockout_duration = timedelta(minutes=settings.LOCKOUT_DURATION)

    # Хеширование пароля с использованием bcrypt
    def hash_password(self, password: str) -> str:
        """
        Хеширование пароля с использованием bcrypt
        :param password: Пароль в виде строки
        :return: Хешированный пароль
        """
        return self.pwd_context.hash(password)

    # Проверка пароля
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Проверка пароля
        :param plain_password: Пароль в виде строки
        :param hashed_password: Хешированный пароль
        :return: True, если пароль верный, иначе False
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    # Валидация пароля по требованиям безопасности
    def validate_password(self, password: str) -> tuple[bool, list[str]]:
        """
        Расширенная валидация пароля с оценкой сложности
        """
        errors = []
        
        if len(password) < self.min_length:
            errors.append(f"Пароль должен быть не менее {self.min_length} символов")
        
        if not re.search(r"[A-Z]", password):
            errors.append("Пароль должен содержать хотя бы одну заглавную букву")
        
        if not re.search(r"[a-z]", password):
            errors.append("Пароль должен содержать хотя бы одну строчную букву")
        
        if not re.search(r"\d", password):
            errors.append("Пароль должен содержать хотя бы одну цифру")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Пароль должен содержать хотя бы один специальный символ")

        return len(errors) == 0, errors

    # Генерация случайного пароля
    def generate_random_password(self, length: int = 12) -> str:
        """
        Генерация случайного пароля
        :param length: Длина пароля
        :return: Случайный пароль
        """
        return ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=length))
    
    # Проверка блокировки
    async def check_brute_force(self, user) -> bool:
        """
        Проверка блокировки
        :param user: Пользователь
        :return: True, если пользователь заблокирован, иначе False
        """
        if user.locked_until and user.locked_until > datetime.utcnow():
            return True
        return False

    # Обработка неудачных попыток входа
    async def handle_failed_login(self, user) -> None:
        """
        Обработка неудачных попыток входа
        :param user: Пользователь
        """
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= self.max_failed_attempts:
            user.locked_until = datetime.utcnow() + self.lockout_duration

    # Сброс неудачных попыток
    async def reset_failed_attempts(self, user) -> None:
        """
        Сброс неудачных попыток
        :param user: Пользователь
        """
        user.failed_login_attempts = 0
        user.locked_until = None

password_manager = PasswordManager()
