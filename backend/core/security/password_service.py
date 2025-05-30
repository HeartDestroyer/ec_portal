# backend/core/security/password_service.py - Класс для работы с паролями

from passlib.context import CryptContext
from datetime import timedelta
import secrets
import string
from typing import Tuple, List

from core.config.config import settings
from core.extensions.logger import logger

class PasswordManager:
    """
    Класс для работы с паролями \n
    Методы:
        - `hash_password` - Хеширование пароля с использованием bcrypt
        - `verify_password` - Проверка password на соответствие hashed_password
        - `validate_password` - Расширенная валидация пароля с оценкой сложности
        - `generate_random_password` - Генерация случайного пароля

    """

    def __init__(self):
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=settings.BCRYPT_ROUNDS
        )
        self.min_length = settings.MIN_LENGTH
        self.max_failed_attempts = settings.MAX_FAILED_ATTEMPTS
        self.lockout_duration = timedelta(minutes=settings.LOCKOUT_DURATION)

        # Предопределенные наборы символов для генерации пароля
        self.uppercase_letters = string.ascii_uppercase
        self.lowercase_letters = string.ascii_lowercase
        self.digits = string.digits
        self.special_chars = "!@#$%^&*(),.?\":{}|<>"
        self.all_chars = self.uppercase_letters + self.lowercase_letters + self.digits + self.special_chars

    def hash_password(self, password: str) -> str:
        """
        Хеширование пароля с использованием bcrypt\n
        `password` - Пароль для хеширования\n
        Возвращает хешированный пароль
        """
        try:
            return self.pwd_context.hash(password)
        except Exception as err:
            logger.error(f"[hash_password] Ошибка при хешировании пароля: {err}")
            raise ValueError("Не удалось хешировать пароль")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Проверка password на соответствие hashed_password\n
        `plain_password` - Пароль в виде строки\n
        `hashed_password` - Хешированный пароль\n
        Возвращает True, если пароль верный, иначе False
        """
        if not plain_password or not hashed_password:
            # Выполняем dummy операцию для защиты от timing attacks
            self.pwd_context.hash("dummy_password")
            return False
        
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except Exception as err:
            logger.error(f"[verify_password] Ошибка при проверке пароля: {err}")
            return False

    def validate_password(self, password: str) -> Tuple[bool, List[str]]:
        """
        Расширенная валидация пароля с оценкой сложности\n
        `password` - Пароль в виде строки\n
        Возвращает кортеж из булева значения и списка ошибок
        """
        if not password:
            return False, ["Пароль не может быть пустым"]
            
        try:
            errors = []
            
            if len(password) < self.min_length:
                errors.append(f"Пароль должен быть не менее {self.min_length} символов")
            
            if not any(char in self.uppercase_letters for char in password):
                errors.append("Пароль должен содержать хотя бы одну заглавную букву")
            
            if not any(char in self.lowercase_letters for char in password):
                errors.append("Пароль должен содержать хотя бы одну строчную букву")
            
            if not any(char in self.digits for char in password):
                errors.append("Пароль должен содержать хотя бы одну цифру")
            
            if not any(char in self.special_chars for char in password):
                errors.append("Пароль должен содержать хотя бы один специальный символ")

            return len(errors) == 0, errors
        except Exception as err:
            logger.error(f"[validate_password] Ошибка при валидации пароля: {err}")
            return False, ["Ошибка при валидации пароля"]

    def generate_random_password(self, length: int = 12) -> str:
        """
        Генерация случайного пароля\n
        `length` - Длина пароля\n
        Возвращает случайный пароль, соответствующий требованиям безопасности
        """
        if length < self.min_length:
            length = self.min_length
            
        try:
            # Гарантируем наличие всех типов символов
            password = [
                secrets.choice(self.uppercase_letters),
                secrets.choice(self.lowercase_letters),
                secrets.choice(self.digits),
                secrets.choice(self.special_chars)
            ]
            
            # Добавляем остальные символы
            for _ in range(length - 4):
                password.append(secrets.choice(self.all_chars))

            # Перемешиваем криптографически безопасно
            for i in range(len(password) - 1, 0, -1):
                j = secrets.randbelow(i + 1)
                password[i], password[j] = password[j], password[i]

            return ''.join(password)
        
        except Exception as err:
            logger.error(f"[generate_random_password] Ошибка при генерации случайного пароля: {err}")
            raise ValueError("Не удалось сгенерировать пароль")
    
password_manager = PasswordManager()
