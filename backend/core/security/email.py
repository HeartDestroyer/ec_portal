# backend/core/security/email.py

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi_mail.errors import ConnectionErrors
from pydantic import EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from jose import jwt, JWTError
from jinja2 import Environment, FileSystemLoader
from core.config.config import settings
from core.extensions.logger import logger
import uuid

class EmailManager:
    """
    Менеджер для отправки email с использованием шаблонов
    """
    def __init__(self):
        """
        Инициализация менеджера email с настройками из конфига
        """
        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=settings.MAIL_DEFAULT_SENDER,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_STARTTLS=settings.MAIL_TLS,
            MAIL_SSL_TLS=settings.MAIL_SSL,
            MAIL_FROM_NAME=settings.PROJECT_NAME,
            USE_CREDENTIALS=True
        )

        self.verify_email_template = 'verify_email'
        self.reset_password_template = 'reset_password'
        self.welcome_email_template = 'welcome'
        self.notification_email_template = 'notification'
        
        template_folder = Path(__file__).parent.parent.parent / 'templates' / 'email'
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_folder)),
            autoescape=True
        )

        self.fastmail = FastMail(self.conf)

    async def _send_email(
        self,
        email_to: EmailStr,
        subject: str,
        template_name: str,
        template_data: Dict[str, Any],
        cc: List[EmailStr] = None,
    ) -> bool:
        """
        Базовый метод для отправки email с использованием шаблона
        
        :param email_to: `email` получателя
        :param subject: Тема письма
        :param template_name: Имя файла шаблона
        :param template_data: Данные для шаблона
        :param cc: Список адресов для копии
        :return: bool: `True` если отправка успешна, `False` в случае ошибки
        """
        try:
            # Получаем шаблон и рендерим его
            template = self.jinja_env.get_template(f"{template_name}.html")
            html_content = template.render(**template_data)

            # Создаем схему сообщения
            message = MessageSchema(
                subject=subject,
                recipients=[email_to] if isinstance(email_to, str) else email_to,
                body=html_content,
                cc=cc if cc else [],
                subtype="html"
            )

            # Отправляем email
            await self.fastmail.send_message(message, template_name=template_name)
            logger.info(f"Письмо успешно отправлено {email_to}")
            return True

        except ConnectionErrors as err:
            logger.error(f"Не удалось отправить письмо {email_to}: {err}")
            return False
        except Exception as err:
            logger.error(f"Непредвиденная ошибка при отправке письма {email_to}: {err}")
            return False

    # Создает подписанный `JWT` токен для `email` верификации/сброса пароля
    def _create_token(self, data: Dict[str, Any], expires_delta: timedelta) -> str:
        """
        Создает подписанный `JWT` токен для `email` верификации/сброса пароля
        :param data: Данные для токена
        :param expires_delta: Срок действия токена
        :return: str: Подписанный JWT токен
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
        return jwt.encode(
            to_encode,
            settings.SECRET_KEY_SIGNED_URL,
            algorithm=settings.JWT_ALGORITHM
        )


    # Проверяет JWT токен для email верификации/сброса пароля
    def verify_token(self, token: str, token_type: str) -> Optional[Dict[str, Any]]:
        """
        Проверяет `JWT` токен для `email` верификации/сброса пароля
        
        :param token: JWT токен для проверки
        :param token_type: Тип токена (`email_verification` или `password_reset`)
        :return: Optional[Dict]: Данные из токена или `None` если токен невалиден
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY_SIGNED_URL,
                algorithms=[settings.JWT_ALGORITHM]
            )
            if payload.get("type") != token_type:
                return None
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning(f"Истек срок действия {token_type} токена")
            return None
        except JWTError as err:
            logger.error(f"Недействительный {token_type} токен: {err}")
            return None


    # Отправляет email для подтверждения адреса
    async def send_verification_email(self, email: EmailStr, user_id: uuid.UUID) -> bool:
        """
        Отправляет `email` для подтверждения адреса
        
        :param email: `email` пользователя
        :param user_id: ID пользователя
        :return: bool: True если отправка успешна
        """
        # Создаем токен для верификации
        token = self._create_token(
            {"sub": str(user_id), "type": "email_verification"},
            timedelta(hours=24)
        )

        # Формируем URL для верификации
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

        # Отправляем email
        return await self._send_email(
            email_to=email,
            subject="Подтверждение email адреса",
            template_name=self.verify_email_template,
            template_data={
                "verification_url": verification_url,
                "project_name": settings.PROJECT_NAME,
                "expire_hours": 24
            }
        )


    # Отправляет email для сброса пароля
    async def send_password_reset_email(self, email: EmailStr, user_id: uuid.UUID) -> bool:
        """
        Отправляет `email` для сброса пароля
        
        :param email: `email` пользователя
        :param user_id: ID пользователя
        :return: bool: True если отправка успешна
        """
        # Создаем токен для сброса пароля
        token = self._create_token(
            {"sub": str(user_id), "type": "password_reset"},
            timedelta(hours=1)
        )

        # Формируем URL для сброса пароля
        reset_url = f"{settings.FRONTEND_URL}/api/v1/auth/reset-password?token={token}"

        # Отправляем email
        return await self._send_email(
            email_to=email,
            subject="Сброс пароля",
            template_name=self.reset_password_template,
            template_data={
                "reset_url": reset_url,
                "project_name": settings.PROJECT_NAME,
                "expire_hours": 1
            }
        )

    # Отправляет приветственное письмо новому пользователю
    async def send_welcome_email(self, email: EmailStr, username: str) -> bool:
        """
        Отправляет приветственное письмо новому пользователю
        
        :param email: `email` пользователя
        :param login: `login` пользователя
        :return: bool: True если отправка успешна
        """
        return await self._send_email(
            email_to=email,
            subject=f"Добро пожаловать в {settings.PROJECT_NAME}!",
            template_name=self.welcome_email_template,
            template_data={
                "username": username,
                "project_name": settings.PROJECT_NAME,
                "support_email": settings.MAIL_DEFAULT_SENDER
            }
        )

    # Отправляет уведомление пользователю
    async def send_notification_email(
        self,
        email: EmailStr,
        subject: str,
        message: str,
        template_data: Dict[str, Any] = None
    ) -> bool:
        """
        Отправляет уведомление пользователю

        :param email: `email` получателя
        :param subject: Тема письма
        :param message: Текст сообщения
        :param template_data: Дополнительные данные для шаблона
        :return: bool: True если отправка успешна
        """
        data = {
            "message": message,
            "project_name": settings.PROJECT_NAME
        }
        if template_data:
            data.update(template_data)

        return await self._send_email(
            email_to=email,
            subject=subject,
            template_name=self.notification_email_template,
            template_data=data
        )

email_manager = EmailManager()
