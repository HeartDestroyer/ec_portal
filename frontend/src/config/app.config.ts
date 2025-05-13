/**
 * Конфигурация приложения
 */

import { RoutePaths } from '@/types/routes.types';

export const API_CONFIG = {
    BASE_URL: import.meta.env.VITE_BACKEND_URL,
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
        SESSIONS: {
            SESSIONS: '/api/v1/session/sessions',
            ADMIN_SESSIONS: '/api/v1/session/sessions/all',
        },
        USER: {
            INFO: '/api/v1/auth/me',
        },
        CACHE: {
            CLEAR: '/api/v1/cache/clear'
        }
    },
} as const;

export const APP_CONFIG = {
    NAME: import.meta.env.VITE_APP_NAME,
    VERSION: import.meta.env.VITE_APP_VERSION,
    ROUTES: {
        PUBLIC: {
            START: '/',
            LOGIN: '/login',
            REGISTER: '/register',
            VERIFY_EMAIL: '/verify-email',
            PASSWORD_RECOVERY: '/password-recovery',
            RESET_PASSWORD: '/reset-password',
            NOT_FOUND: '/404',
        } as RoutePaths['PUBLIC'],
        PRIVATE: {
            START: '/',
            ADMIN: '/admin',
            PROFILE: '/profile',
            LETTER: '/letter',
            ACHIEVEMENTS: '/achievements',
            EMPLOYEES: '/employees',
            COMPANY_STRUCTURE: '/company-structure',
            LEADER: '/education',
            MASTERCLASS: '/masterclass',
            LESSONS: '/lessons',
            CHECKLIST: '/checklist',
            HR_TESTING: '/candidates',
            PRESENTATION: '/presentation',
            OBJECTIONS: '/objections',
            REVIEWS: '/reviews',
            CALCULATOR: '/calculator',
            RESPONSIBLE: '/responsible',
            AUDIO_OBJECTIONS: '/audio-objections',
            SHOP: '/shop',
            SETTINGS: '/settings',
            SESSIONS: '/sessions',
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
    PHONE: {
        PATTERN: /^(\+7|8)?[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}$/,
    },
    EMAIL: {
        PATTERN: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    },
    NAME: {
        MIN_LENGTH: 5,
        MAX_LENGTH: 100,
    },
} as const;
