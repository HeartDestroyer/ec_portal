# backend/core/interfaces/__init__.py - Интерфейсы для сервисов и репозиториев

from core.interfaces.auth.auth_repositories import UserRepositoryInterface
from core.interfaces.auth.auth_services import (
    AuthenticationServiceInterface, RegistrationServiceInterface, PasswordServiceInterface, EmailServiceInterface, TwoFactorServiceInterface
)

from core.interfaces.session.session_repositories import SessionRepositoryInterface
from core.interfaces.session.session_services import SessionServiceInterface

__all__ = [
    "UserRepositoryInterface",
    "AuthenticationServiceInterface",
    "RegistrationServiceInterface",
    "PasswordServiceInterface",
    "EmailServiceInterface",
    "TwoFactorServiceInterface",
    "SessionServiceInterface",
    "SessionRepositoryInterface"
]
