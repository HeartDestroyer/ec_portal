/**
 * Конфигурация приложения
 * Содержит базовые настройки API:
 * - Адрес бэкенда
 * - Пути API эндпоинтов
 * - Ключи для хранения токенов
 * Настройки приложения:
 * - Имя приложения
 * - Версия приложения
 * - Ключи для хранения пользователя в localStorage
 * - Пути маршрутизации
 * - Правила валидации
 */

import { RoutePaths } from '@/types/routes.types';

export const API_CONFIG = {
    BASE_URL: process.env.BACKEND_URL,
    TOKEN: {
        ACCESS: 'access_token',
        REFRESH: 'refresh_token'
    },
    ENDPOINTS: {
        AUTH: {
            REGISTER: '/api/v1/auth/register',
            LOGIN: '/api/v1/auth/login',
            REFRESH: '/api/v1/auth/refresh',
            LOGOUT: '/api/v1/auth/logout',
            REQUEST_PASSWORD_RESET: '/api/v1/auth/request-password-reset',
            RESET_PASSWORD: '/api/v1/auth/reset-password',
            VERIFY_EMAIL: '/api/v1/auth/verify-email',
            RESEND_VERIFICATION: '/api/v1/auth/resend-verification',
            CSRF: '/api/v1/auth/csrf',
        },
        USER: {
            INFO: '/api/v1/user/me',
        },
    },
} as const;

export const APP_CONFIG = {
    NAME: import.meta.env.VITE_APP_NAME,
    VERSION: import.meta.env.VITE_APP_VERSION,
    STORAGE_KEYS: {
        USER: 'user'
    },
    ROUTES: {
        PUBLIC: {
            LOGIN: '/login',
            REGISTER: '/register',
            PASSWORD_RECOVERY: '/password-recovery',
            RESET_PASSWORD: '/reset-password',
            NOT_FOUND: '/404',
        } as RoutePaths['PUBLIC'],
        PRIVATE: {
            DASHBOARD: '/dashboard',
        } as RoutePaths['PRIVATE'],
    },
} as const;

export const VALIDATION_CONFIG = {
    PASSWORD: {
        MIN_LENGTH: 8,
        MAX_LENGTH: 32,
        PATTERN: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/,
    },
    USERNAME: {
        MIN_LENGTH: 3,
        MAX_LENGTH: 20,
        PATTERN: /^[a-zA-Z0-9_]+$/,
    },
    EMAIL: {
        PATTERN: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    },
} as const;
