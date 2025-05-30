# backend/core/security/email_service.py - Email сервис для отправки email с использованием шаблонов

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi_mail.errors import ConnectionErrors
from tenacity import retry, stop_after_attempt, wait_exponential
from pydantic import EmailStr
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template
from fastapi import HTTPException
from email_validator import validate_email, EmailNotValidError
import asyncio

from core.config.config import settings
from core.extensions.logger import logger
from backend.core.security.jwt_service import jwt_handler

class EmailManager:
    """
    Менеджер для отправки email с использованием шаблонов
    
    Методы:
        - `send_verification_email` - Отправка email для подтверждения со сроком действия\n
        - `send_password_reset_email` - Отправка email для сброса пароля со сроком действия\n
        - `send_welcome_email` - Отправка приветственного письма новому пользователю\n
        - `send_notification_email` - Отправка уведомления пользователю\n
        - `send_bulk_emails` - Отправка email нескольким получателям используя шаблон уведомлений notification_email_template
    """

    def __init__(self):
        self.conf = self._create_connection_config()
        self._setup_templates()
        self._setup_urls()
        self._setup_project_info()
        self.fastmail = FastMail(self.conf)
        self._setup_jinja_environment()

    def _create_connection_config(self) -> ConnectionConfig:
        return ConnectionConfig(
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
        
    def _setup_templates(self) -> None:
        self.verify_email_template = 'verify_email'
        self.reset_password_template = 'reset_password'
        self.welcome_email_template = 'welcome'
        self.notification_email_template = 'notification'
    
    def _setup_urls(self) -> None:
        self.verification_url = f"{settings.FRONTEND_URL}/verify-email"
        self.reset_url = f"{settings.FRONTEND_URL}/password-recovery"
        
    def _setup_jinja_environment(self) -> None:
        template_folder = Path(__file__).parent.parent.parent / 'templates' / 'email'
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_folder)),
            autoescape=True
        )
        
    def _setup_project_info(self) -> None:
        self.project_name = settings.PROJECT_NAME
        self.mail_default_sender = settings.MAIL_DEFAULT_SENDER
        
    
    def _validate_email(self, email: EmailStr) -> bool:
        """
        Метод для проверки email на валидность\n
        `email` - `email` для проверки\n
        Возвращает True если email валиден, False в случае ошибки
        """
        try:
            validation_result = validate_email(email)
            logger.debug(f"[validate_email] Почта «{email}» прошла валидацию: {validation_result.normalized}")
            return True
        except EmailNotValidError as err:
            logger.warning(f"[validate_email] Почта «{email}» не прошла валидацию: {err}")
            return False
    
    def _get_template(self, template_name: str) -> Template:
        """
        Метод для получения шаблона\n
        `template_name` - Имя файла шаблона\n
        Возвращает шаблон в виде Template, в случае ошибки возвращает ValueError
        """
        try:
            return self.jinja_env.get_template(f"{template_name}.html")
        except Exception as err:
            logger.error(f"[get_template] Ошибка при получении шаблона письма {template_name}: {err}")
            raise ValueError(f"Не удалось получить шаблон письма")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _send_email(self, email_to: Union[EmailStr, List[EmailStr]], subject: str, template_name: str, template_data: Dict[str, Any], cc: Optional[List[EmailStr]] = None) -> bool:
        """
        Базовый метод для отправки email с использованием шаблона с проверкой email на валидность\n
        `email_to` - `email` получателя\n
        `subject` - Тема письма\n
        `template_name` - Имя файла шаблона\n
        `template_data` - Данные для шаблона\n
        `cc` - Список адресов для копии\n
        Возвращает True если отправка успешна, False в случае ошибки
        """
        try:
            template = self._get_template(template_name)
            html_content = template.render(**template_data)
            
            validate_emails = []

            if isinstance(email_to, list):
                for email in email_to:
                    if not self._validate_email(email):
                        logger.warning(f"[send_email] Невалидный email: {email}")
                        return False
                    validate_emails.append(email)
            else:
                if not self._validate_email(email_to):
                    logger.warning(f"[send_email] Невалидный email: {email_to}")
                    return False
                validate_emails.append(email_to)

            message = MessageSchema(
                subject=subject, 
                recipients=validate_emails,
                body=html_content, 
                cc=cc if cc else [], 
                subtype="html"
            )

            await self.fastmail.send_message(message, template_name=template_name)
            logger.info(f"[send_email] Письмо '{subject}' успешно отправлено на {email_to}")
            return True

        except ConnectionErrors as err:
            logger.error(f"[send_email] Не удалось отправить письмо '{subject}' на {email_to}: {err}")
            return False
        except Exception as err:
            logger.error(f"[send_email] Непредвиденная ошибка при отправке письма '{subject}' на {email_to}: {err}")
            return False

    
    async def send_verification_email(self, email: EmailStr, user_id: str) -> bool:
        """
        Отправляет email для подтверждения со сроком действия\n
        `email` - `email` пользователя\n
        `user_id` - ID пользователя\n
        Возвращает True если отправка успешна, False в случае ошибки
        """
        try:
            token = jwt_handler.create_verification_token(user_id)
            expire_hours = jwt_handler.time_delta_verification.total_seconds() / 3600
            
            return await self._send_email(
                email_to=email,
                subject=f"Подтверждение почты на {self.project_name}е",
                template_name=self.verify_email_template,
                template_data={
                    "verification_url": f"{self.verification_url}?token={token}",
                    "project_name": self.project_name,
                    "expire_hours": expire_hours
                }
            )
        
        except HTTPException as err:
            logger.error(f"[send_verification_email] HTTP ошибка при создании токена верификации для {user_id}: {err.detail}")
            return False
        except Exception as err:
            logger.error(f"[send_verification_email] Ошибка при отправке письма для подтверждения на {email}: {err}")
            return False

    async def send_password_reset_email(self, email: EmailStr, user_id: str) -> bool:
        """
        Отправляет email для сброса пароля со сроком действия\n
        `email` - `email` пользователя\n
        `user_id` - ID пользователя\n
        Возвращает True если отправка успешна, False в случае ошибки
        """
        try:
            token = jwt_handler.create_reset_token(user_id)
            expire_hours = jwt_handler.time_delta_reset.total_seconds() / 3600
            
            logger.debug(f"[send_password_reset_email] Отправка письма для сброса пароля на {email}")
            return await self._send_email(
                email_to=email,
                subject=f"Сброс пароля на {self.project_name}е",
                template_name=self.reset_password_template,
                template_data={
                    "reset_url": f"{self.reset_url}?token={token}",
                    "project_name": self.project_name,
                    "expire_hours": expire_hours
                }
            )
        
        except HTTPException as err:
            logger.error(f"[send_password_reset_email] HTTP ошибка при создании токена сброса пароля для {user_id}: {err.detail}")
            return False
        except Exception as err:
            logger.error(f"[send_password_reset_email] Ошибка при отправке письма для сброса пароля на {email}: {err}")
            return False

    async def send_welcome_email(self, email: EmailStr, username: str) -> bool:
        """
        Отправляет приветственное письмо новому пользователю\n
        `email` - `email` пользователя\n
        `username` - Имя пользователя\n
        Возвращает True если отправка успешна, False в случае ошибки
        """
        try:
            return await self._send_email(
                email_to=email,
                subject=f"Добро пожаловать в {self.project_name}е",
                template_name=self.welcome_email_template,
                template_data={
                    "username": username,
                    "project_name": self.project_name,
                    "support_email": self.mail_default_sender
                }
            )
        
        except Exception as err:
            logger.error(f"[send_welcome_email] Ошибка при отправке приветственного письма на {email}: {err}")
            return False

    async def send_notification_email(self, email: EmailStr, subject: str, message: str, template_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Отправляет уведомление пользователю\n
        `email` - `email` получателя\n
        `subject` - Тема письма\n
        `message` - Текст сообщения\n
        `template_data` - Дополнительные данные для шаблона\n
        Возвращает True если отправка успешна, False в случае ошибки
        """
        try:
            data = {
                "message": message,
                "project_name": f"Уведомление от {self.project_name}а"
            }
            if template_data:
                data.update(template_data)
            
            return await self._send_email(
                email_to=email,
                subject=subject,
                template_name=self.notification_email_template,
                template_data=data
            )
        
        except Exception as err:
            logger.error(f"[send_notification_email] Ошибка при отправке уведомления '{subject}' на {email}: {err}")
            return False

    async def send_bulk_emails(self, emails: List[EmailStr], subject: str, message: str, delay_between_sends: float = 0.1) -> None:
        """
        Отправка email нескольким получателям используя шаблон уведомлений notification_email_template\n
        `emails` - Список email получателей\n
        `subject` - Тема письма\n
        `message` - Текст сообщения\n
        `delay_between_sends` - Задержка между отправками в секундах
        """
        successful_sends = 0
        failed_sends = 0

        try:
            data = {
                "message": message,
                "project_name": f"Уведомление от {self.project_name}а"
            }

            for i, email in enumerate(emails):
                try:
                    await self._send_email(email, subject, template_name=self.notification_email_template, template_data=data)
                    successful_sends += 1
                    if i < len(emails) - 1:
                        await asyncio.sleep(delay_between_sends)
                except Exception:
                    failed_sends += 1
                    
            logger.info(f"[send_bulk_emails] Массовая рассылка завершена: {successful_sends}/{len(emails)} успешных отправок, {failed_sends} неуспешных отправок")
            
        except Exception as err:
            logger.error(f"[send_bulk_emails] Ошибка при отправке уведомления «{subject}» на {emails}: {err}")

email_manager = EmailManager()
