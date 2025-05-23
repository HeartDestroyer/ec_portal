from passlib.context import CryptContext
from datetime import datetime, timedelta
import random
import string
from typing import Tuple, List

from core.config.config import settings
from core.models.user import User
from core.extensions.logger import logger

class PasswordManager:
    """
    Класс для работы с паролями
    Класс выполняет следующие функции:
    - Хеширование пароля с использованием bcrypt
    - Проверка password на соответствие hashed_password
    - Расширенная валидация пароля с оценкой сложности
    - Генерация случайного пароля
    - Проверка блокировки
    - Обработка неудачных попыток входа
    - Сброс неудачных попыток
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

    def hash_password(self, password: str) -> str:
        """
        Хеширование пароля с использованием bcrypt\n
        `password` - Пароль для хеширования\n
        Возвращает хешированный пароль
        """
        try:
            return self.pwd_context.hash(password)
        except Exception as err:
            logger.error(f"Ошибка при хешировании пароля: {err}")
            raise ValueError("Не удалось хешировать пароль")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Проверка password на соответствие hashed_password\n
        `plain_password` - Пароль в виде строки\n
        `hashed_password` - Хешированный пароль\n
        Возвращает True, если пароль верный, иначе False
        """            
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except Exception as err:
            logger.error(f"Ошибка при проверке пароля: {err}")
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
            logger.error(f"Ошибка при валидации пароля: {err}")
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
                random.choice(self.uppercase_letters),
                random.choice(self.lowercase_letters),
                random.choice(self.digits),
                random.choice(self.special_chars)
            ]
            
            # Добавляем остальные символы
            all_chars = self.uppercase_letters + self.lowercase_letters + self.digits + self.special_chars
            password.extend(random.choices(all_chars, k=length-4))
            return ''.join(random.shuffle(password))
        
        except Exception as err:
            logger.error(f"Ошибка при генерации случайного пароля: {err}")
            raise ValueError("Не удалось сгенерировать пароль")
    
    async def check_brute_force(self, user: User) -> bool:
        """
        Проверка блокировки\n
        `user` - Пользователь\n
        Возвращает True, если пользователь заблокирован, иначе False
        """
        try:
            if user.locked_until and user.locked_until > datetime.utcnow():
                return True
            elif user.locked_until:
                user.failed_login_attempts = 0
                user.locked_until = None
            return False
        except Exception as err:
            logger.error(f"Ошибка при проверке блокировки: {err}")
            return False

    async def handle_failed_login(self, user: User) -> None:
        """
        Обработка неудачных попыток входа\n
        `user` - Пользователь\n
        """
        try:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= self.max_failed_attempts:
                user.locked_until = datetime.utcnow() + self.lockout_duration
                logger.warning(f"Пользователь {user.login} заблокирован до {user.locked_until}")
        except Exception as err:
            logger.error(f"Ошибка при обработке неудачной попытки входа: {err}")
            raise ValueError("Не удалось обработать неудачную попытку входа")

    async def reset_failed_attempts(self, user: User) -> None:
        """
        Сброс неудачных попыток\n
        `user` - Пользователь
        """
        try:
            user.failed_login_attempts = 0
            user.locked_until = None
        except Exception as err:
            logger.error(f"Ошибка при сбросе неудачных попыток: {err}")
            raise ValueError("Не удалось сбросить неудачные попытки")

password_manager = PasswordManager()
