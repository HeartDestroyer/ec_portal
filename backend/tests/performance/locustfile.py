from locust import HttpUser, task, between
import random
import string

# Класс для тестирования API
class APITestUser(HttpUser):
    """
    Класс для тестирования API
    """
    wait_time = between(1, 3)  # Время ожидания между запросами
    host = "http://127.0.0.1:8000"  # Базовый URL API

    # Выполняется при старте каждого пользователя
    def on_start(self):
        """
        Выполняется при старте каждого пользователя
        """
        self.login()

    # Генерация случайной строки
    def generate_random_string(self, length: int = 10) -> str:
        """
        Генерация случайной строки
        :param length: Длина строки
        :return: Случайная строка
        """
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    # Аутентификация пользователя
    def login(self):
        """
        Аутентификация пользователя
        :return: Токен доступа
        """
        login_data = {
            "login_or_email": "test@example.com",
            "password": "Test123!"
        }
        response = self.client.post("/api/v1/auth/login", json=login_data)
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}

    # Получение данных текущего пользователя
    @task(3)
    def get_current_user(self):
        """
        Получение данных текущего пользователя
        :return: Данные текущего пользователя
        """
        self.client.get("/api/v1/auth/me", headers=self.headers)

    # Обновление токена
    @task(2)
    def refresh_token(self):
        """
        Обновление токена
        :return: Новый токен доступа
        """
        self.client.post("/api/v1/auth/refresh", headers=self.headers)

    # Регистрация нового пользователя
    @task(1)
    def register_user(self):
        """
        Регистрация нового пользователя
        :return: Новый пользователь
        """
        user_data = {
            "login": f"test_{self.generate_random_string()}",
            "email": f"test_{self.generate_random_string()}@example.com",
            "name": f"Test User {self.generate_random_string()}",
            "password": "Test123!",
            "phone": "+79991234567"
        }
        self.client.post("/api/v1/auth/register", json=user_data)

    # Запрос на сброс пароля
    @task(2)
    def request_password_reset(self):
        """
        Запрос на сброс пароля
        :return: Сброс пароля
        """
        data = {"email": "test@example.com"}
        self.client.post("/api/v1/auth/request-password-reset", json=data)

    # Подтверждение email
    @task(1)
    def verify_email(self):
        """
        Подтверждение email
        :return: Подтверждение email
        """
        data = {"token": "test_token"}
        self.client.post("/api/v1/auth/verify-email", json=data)

    # Выход из системы
    @task(1)
    def logout(self):
        """
        Выход из системы
        :return: Выход из системы
        """
        self.client.post("/api/v1/auth/logout", headers=self.headers)

    # Получение CSRF токена
    @task(3)
    def get_csrf_token(self):
        """
        Получение CSRF токена
        :return: CSRF токен
        """
        self.client.get("/api/v1/auth/csrf", headers=self.headers)
