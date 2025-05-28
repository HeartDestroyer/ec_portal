# backend/core/interfaces/__init__.py - Интерфейсы для сервисов и репозиториев

from core.interfaces.auth.auth_repositories import UserRepositoryInterface, SessionRepositoryInterface
from core.interfaces.auth.auth_services import (
    AuthenticationServiceInterface, RegistrationServiceInterface, PasswordServiceInterface, EmailServiceInterface, TwoFactorServiceInterface
)

__all__ = [
    "UserRepositoryInterface",
    "SessionRepositoryInterface", 
    "AuthenticationServiceInterface",
    "RegistrationServiceInterface",
    "PasswordServiceInterface",
    "EmailServiceInterface",
    "TwoFactorServiceInterface"
]
