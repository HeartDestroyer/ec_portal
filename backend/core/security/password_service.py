# backend/core/security/password_service.py - Менеджер для работы с паролями

from passlib.context import CryptContext
from datetime import timedelta, datetime
import secrets
import string
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass
from pydantic import Field

from core.config.config import settings
from core.extensions.logger import logger

class PasswordStrength(Enum):
    """
    Уровни сложности пароля
    """
    WEAK = "слабый"
    MEDIUM = "средний"
    STRONG = "сильный"

@dataclass
class PasswordValidationResult:
    """
    Результат валидации пароля
    """
    is_valid: bool = Field(..., description="Валидность пароля")
    errors: List[str] = Field(..., description="Ошибки валидации")
    strength: PasswordStrength = Field(..., description="Сложность пароля")
    score: int = Field(..., description="Оценка сложности")

@dataclass
class BruteForceStatus:
    """
    Статус защиты от брутфорса
    """
    is_locked: bool = Field(..., description="Блокировка")
    attempts_remaining: int = Field(..., description="Оставшиеся попытки")
    locked_until: Optional[datetime] = Field(None, description="Время блокировки")
    lockout_duration: Optional[timedelta] = Field(None, description="Длительность блокировки")

class PasswordManager:
    """
    Абстрактный менеджер паролей
    
    Методы:
        - `hash_password` - Хеширование пароля с использованием bcrypt
        - `verify_password` - Проверка password на соответствие hashed_password
        - `validate_password` - Расширенная валидация пароля с оценкой сложности
        - `generate_random_password` - Генерация случайного пароля
        - `should_lock_user` - Определяет, нужно ли блокировать пользователя
        - `calculate_lockout_end_time` - Вычисляет время окончания блокировки
        - `calculate_lockout_status` - Вычисляет статус блокировки на основе данных (не изменяет состояние)
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
        if not password:
            raise ValueError("Пароль не может быть пустым")
        
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

    def validate_password(self, password: str) -> PasswordValidationResult:
        """
        Расширенная валидация пароля с оценкой сложности\n
        `password` - Пароль в виде строки\n
        Возвращает объект PasswordValidationResult
        """
        if not password:
            return PasswordValidationResult(
                is_valid=False,
                errors=["Пароль не может быть пустым"],
                strength=PasswordStrength.WEAK,
                score=0
            )
            
        try:
            errors = []
            score = 0
            
            # Проверка длины пароля
            if len(password) < self.min_length:
                errors.append(f"Пароль должен быть не менее {self.min_length} символов")
            else:
                score += min(25, len(password) * 2)

            # Проверка типов символов
            char_types = 0

            # Проверка наличия заглавных букв
            if any(char in self.uppercase_letters for char in password):
                score += 20
                char_types += 1
            else:
                errors.append("Пароль должен содержать хотя бы одну заглавную букву")

            # Проверка наличия строчных букв
            if any(char in self.lowercase_letters for char in password):
                score += 20
                char_types += 1
            else:
                errors.append("Пароль должен содержать хотя бы одну строчную букву")

            # Проверка наличия цифр
            if any(char in self.digits for char in password):
                score += 20
                char_types += 1
            else:
                errors.append("Пароль должен содержать хотя бы одну цифру")

            # Проверка наличия специальных символов
            if any(char in self.special_chars for char in password):
                score += 20
                char_types += 1
            else:
                errors.append("Пароль должен содержать хотя бы один специальный символ")

            # Бонус за разнообразие
            if char_types == 4:
                score += 15

            # Определяем силу пароля
            if score >= 90:
                strength = PasswordStrength.VERY_STRONG
            elif score >= 70:
                strength = PasswordStrength.STRONG
            elif score >= 50:
                strength = PasswordStrength.MEDIUM
            else:
                strength = PasswordStrength.WEAK

            return PasswordValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                strength=strength,
                score=min(100, score)
            )
        
        except Exception as err:
            logger.error(f"[validate_password] Ошибка при валидации пароля: {err}")
            return PasswordValidationResult(
                is_valid=False,
                errors=["Ошибка при валидации пароля"],
                strength=PasswordStrength.WEAK,
                score=0
            )

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

            generated_password = ''.join(password)
            return generated_password
        
        except Exception as err:
            logger.error(f"[generate_random_password] Ошибка при генерации случайного пароля: {err}")
            raise ValueError("Не удалось сгенерировать пароль")
    
    def should_lock_user(self, failed_attempts: int) -> bool:
        """
        Определяет, нужно ли блокировать пользователя\n
        `failed_attempts` - Количество неудачных попыток\n
        Возвращает True, если нужно блокировать
        """
        return failed_attempts >= self.max_failed_attempts
    
    def calculate_lockout_end_time(self) -> datetime:
        """
        Вычисляет время окончания блокировки\n
        Возвращает datetime когда блокировка должна закончиться
        """
        return datetime.utcnow() + self.lockout_duration

    def calculate_lockout_status(self, failed_attempts: int, locked_until: Optional[datetime]) -> BruteForceStatus:
        """
        Вычисляет статус блокировки на основе данных (не изменяет состояние)\n
        `failed_attempts` - Количество неудачных попыток\n
        `locked_until` - Время до которого заблокирован пользователь\n
        Возвращает статус блокировки
        """
        current_time = datetime.utcnow()
        
        # Проверяем активную блокировку
        if locked_until and locked_until > current_time:
            return BruteForceStatus(
                is_locked=True,
                attempts_remaining=0,
                locked_until=locked_until,
                lockout_duration=locked_until - current_time
            )
        
        # Вычисляем оставшиеся попытки
        attempts_remaining = max(0, self.max_failed_attempts - failed_attempts)
        
        return BruteForceStatus(
            is_locked=False,
            attempts_remaining=attempts_remaining,
            locked_until=None,
            lockout_duration=None
        )

password_manager = PasswordManager()
