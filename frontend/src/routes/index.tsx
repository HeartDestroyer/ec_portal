import { RouteObject } from 'react-router-dom';
import { APP_CONFIG } from '../config/app.config';
import LoginForm from '../authorization/LoginForm';
import RegisterForm from '../authorization/RegisterForm';
import ResetPassword from '../authorization/ResetPassword';
import NotFound from '../technical/404';

export const publicRoutes: RouteObject[] = [
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
        element: <div>Dashboard</div>
    },
];
