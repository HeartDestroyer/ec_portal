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
}

export interface PrivateRoutes {
    DASHBOARD: string;
    PROFILE: string;
    SETTINGS: string;
}

export interface RoutePaths {
    PUBLIC: PublicRoutes;
    PRIVATE: PrivateRoutes;
} 