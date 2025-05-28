# backend/core/services/__init__.py - Сервисы для работы с данными

from core.services.base_service import BaseService

__all__ = [
    "BaseService", 
    "AuthenticationService", 
    "RegistrationService", 
    "PasswordService", 
    "EmailService"
]
