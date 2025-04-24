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
            MAIL_SSL_TLS=settings.MAIL_SSL,
            MAIL_STARTTLS=settings.MAIL_TLS,
            MAIL_FROM_NAME=settings.PROJECT_NAME,
            USE_CREDENTIALS=True,
            TEMPLATE_FOLDER=Path(__file__).parent.parent.parent / 'templates' / 'email'
        )
        
        self.fastmail = FastMail(self.conf)
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.conf.TEMPLATE_FOLDER)),
            autoescape=True
        )

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
        
        :param email_to: Email получателя
        :param subject: Тема письма
        :param template_name: Имя файла шаблона
        :param template_data: Данные для шаблона
        :param cc: Список адресов для копии
        :return: bool: True если отправка успешна, False в случае ошибки
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
                cc=cc,
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

    def _create_token(self, data: Dict[str, Any], expires_delta: timedelta) -> str:
        """
        Создает подписанный JWT токен для email верификации/сброса пароля
        
        :param data: Данные для токена
        :param expires_delta: Срок действия токена
        :return: str: Подписанный JWT токен
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
        return jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

    # Проверяет JWT токен для email верификации/сброса пароля
    def verify_token(self, token: str, token_type: str) -> Optional[Dict[str, Any]]:
        """
        Проверяет JWT токен для email верификации/сброса пароля
        
        :param token: JWT токен для проверки
        :param token_type: Тип токена ('email_verification' или 'password_reset')
        :return: Optional[Dict]: Данные из токена или None если токен невалиден
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            if payload.get("type") != token_type:
                return None
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning(f"Истек срок действия {token_type} токена")
            return None
        except JWTError as err:
            logger.error(f"Недействительный {token_type} токен: {str(err)}")
            return None

    # Отправляет email для подтверждения адреса
    async def send_verification_email(self, email: EmailStr, user_id: int) -> bool:
        """
        Отправляет email для подтверждения адреса
        
        :param email: Email пользователя
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
            template_name="verify_email",
            template_data={
                "verification_url": verification_url,
                "project_name": settings.PROJECT_NAME,
                "expire_hours": 24
            }
        )

    # Отправляет email для сброса пароля
    async def send_password_reset_email(self, email: EmailStr, user_id: int) -> bool:
        """
        Отправляет email для сброса пароля
        
        :param email: Email пользователя
        :param user_id: ID пользователя
        :return: bool: True если отправка успешна
        """
        # Создаем токен для сброса пароля
        token = self._create_token(
            {"sub": str(user_id), "type": "password_reset"},
            timedelta(hours=1)
        )

        # Формируем URL для сброса пароля
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

        # Отправляем email
        return await self._send_email(
            email_to=email,
            subject="Сброс пароля",
            template_name="reset_password",
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
        
        :param email: Email пользователя
        :param username: Имя пользователя
        :return: bool: True если отправка успешна
        """
        return await self._send_email(
            email_to=email,
            subject=f"Добро пожаловать в {settings.PROJECT_NAME}!",
            template_name="welcome",
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

        :param email: Email получателя
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
            template_name="notification",
            template_data=data
        )

# Создаем глобальный экземпляр для использования в приложении
email_manager = EmailManager()
