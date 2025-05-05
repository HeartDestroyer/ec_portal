
/**
 * Типы для работы с маршрутами
 * Содержит типы для работы с маршрутами
 */

import { ReactNode } from 'react';

export interface RouteConfig {
    path: string;
    element: ReactNode;
    children?: RouteConfig[];
}

export interface PublicRoutes {
    LOGIN: string;
    REGISTER: string;
    PASSWORD_RECOVERY: string;
    RESET_PASSWORD: string;
    NOT_FOUND: string;
    VERIFY_EMAIL: string;
    START: string;
}

export interface PrivateRoutes {
    START: string;
    ADMIN: string;
    PROFILE: string;
    LETTER: string;
    ACHIEVEMENTS: string;
    EMPLOYEES: string;
    COMPANY_STRUCTURE: string;
    LEADER: string;
    MASTERCLASS: string;
    LESSONS: string;
    CHECKLIST: string;
    HR_TESTING: string;
    PRESENTATION: string;
    OBJECTIONS: string;
    REVIEWS: string;
    CALCULATOR: string;
    RESPONSIBLE: string;
    AUDIO_OBJECTIONS: string;
    SHOP: string;
    SETTINGS: string;
}

export interface RoutePaths {
    PUBLIC: PublicRoutes;
    PRIVATE: PrivateRoutes;
} 