
/**
 * Маршруты для авторизации
 * Содержит маршруты для авторизации
 */

import { RouteObject } from 'react-router-dom';
import { APP_CONFIG } from '../config/app.config';
import LoginForm from '../auth/login.form';
import RegisterForm from '../auth/register.form';
import ResetPassword from '../auth/password-recovery.form';
import NotFound from '../technical/404.component';
import Dashboard from '../components/dashboard.components';
import HomeRoute from '../components/home.route';
import VerifyEmailPage from '../auth/verify-email.pages';

export const publicRoutes: RouteObject[] = [
    {
        path: APP_CONFIG.ROUTES.PUBLIC.START,
        element: <HomeRoute />
    },
    {
        path: APP_CONFIG.ROUTES.PUBLIC.VERIFY_EMAIL,
        element: <VerifyEmailPage />
    },
    {
        path: APP_CONFIG.ROUTES.PUBLIC.LOGIN,
        element: <LoginForm />
    },
    {
        path: APP_CONFIG.ROUTES.PUBLIC.REGISTER,
        element: <RegisterForm />
    },
    {
        path: APP_CONFIG.ROUTES.PUBLIC.RESET_PASSWORD,
        element: <ResetPassword />
    },
    {
        path: '*',
        element: <NotFound />
    }
];

export const protectedRoutes: RouteObject[] = [
    {
        path: APP_CONFIG.ROUTES.PRIVATE.DASHBOARD,
        element: <Dashboard />
    },
];
