/**
 * Маршруты для авторизации
 * Содержит маршруты для авторизации
 */
import { lazy } from 'react';
import { RouteObject } from 'react-router-dom';
import { APP_CONFIG } from '../config/app.config';
import { ROLES } from '@/config/roles.config';

// Страницы для авторизации
import LoginForm from '../auth/login.form';
import RegisterForm from '../auth/register.form';
import ResetPassword from '../auth/password-recovery.form';
import VerifyEmailPage from '../auth/verify-email.pages';

import HomeRoute from '../components/home.route';
import NotFound from '../technical/404.component';
import DashboardLayout from '@/technical/layout.page';

// Страницы для административных маршрутов
const AdminPanelPage = lazy(() => import('../admin_panel/admin_panel.page'));

// Страницы для профиля пользователя
const DashboardPage = lazy(() => import('../components/dashboard.page'));
const ProfilePage = lazy(() => import('../profile/components/info.page'));
const AchievementsPage = lazy(() => import('../profile/components/achievements.page'));
const LetterPage = lazy(() => import('../profile/components/letter.page'));

// Страницы для организаций
const EmployeesPage = lazy(() => import('../organizations/components/employees.page'));
const CompanyStructurePage = lazy(() => import('../organizations/components/company_structure.page'));

// Страницы для видео уроков
const VideoLessonsPage = lazy(() => import('../video_lessons/components/video_lessons.page'));
const LeaderLessonsPage = lazy(() => import('../video_lessons/components/leader.page'));
const MasterClassPage = lazy(() => import('../video_lessons/components/master_class.page'));
const CheckListPage = lazy(() => import('../video_lessons/components/check_list.page'));

// Страницы для HR тестирования
const HrPage = lazy(() => import('../candidates/components/hr.page'));

// Страницы для презентации
const PresentationPage = lazy(() => import('../presentation/components/presentation.page'));

// Страницы для возражений о неоплате
const ObjectionsPage = lazy(() => import('../objection/components/objection.page'));

// Страницы для отзывов клиентов
const CustomerReviewsPage = lazy(() => import('../tools_and_assistants/components/customer_reviews.page'));

// Страницы для калькулятора ОТС
const CalculatorOtsPage = lazy(() => import('../tools_and_assistants/components/calculator.page'));

// Страницы для справочника
const ResponsiblePage = lazy(() => import('../tools_and_assistants/components/responsible.page'));

// Страницы для аудио возражений о неоплате
const AudioObjectionsPage = lazy(() => import('../tools_and_assistants/components/audio_objections.page'));

// Страницы для онлайн магазина
const OnlineStorePage = lazy(() => import('../online_store/components/online_store.page'));

// Страницы для настроек
const SettingsPage = lazy(() => import('../settings/components/settings.page'));


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
        path: APP_CONFIG.ROUTES.PRIVATE.START,
        element: <DashboardLayout />,
        children: [
            {
                index: true,
                element: <DashboardPage />,
                allowedRoles: ROLES.ALL
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.ADMIN,  
                element: <AdminPanelPage />,
                allowedRoles: ROLES.ADMIN
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.PROFILE,
                element: <ProfilePage />,
                allowedRoles: ROLES.ALL
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.ACHIEVEMENTS,
                element: <AchievementsPage />,
                allowedRoles: ROLES.WORKERS
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.LETTER,
                element: <LetterPage />,
                allowedRoles: ROLES.WORKERS
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.EMPLOYEES,
                element: <EmployeesPage />,
                allowedRoles: ROLES.WORKERS
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.COMPANY_STRUCTURE,
                element: <CompanyStructurePage />,
                allowedRoles: ROLES.WORKERS
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.LESSONS,
                element: <VideoLessonsPage />,
                allowedRoles: ROLES.WORKERS
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.LEADER,
                element: <LeaderLessonsPage />,
                allowedRoles: ROLES.LEADER
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.MASTERCLASS,
                element: <MasterClassPage />,
                allowedRoles: ROLES.WORKERS
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.CHECKLIST,
                element: <CheckListPage />,
                allowedRoles: ROLES.WORKERS
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.HR_TESTING,
                element: <HrPage />,
                allowedRoles: ROLES.WORKERS
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.PRESENTATION,
                element: <PresentationPage />,
                allowedRoles: ROLES.WORKERS
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.OBJECTIONS,
                element: <ObjectionsPage />,
                allowedRoles: ROLES.WORKERS
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.REVIEWS,
                element: <CustomerReviewsPage />,
                allowedRoles: ROLES.WORKERS
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.CALCULATOR,
                element: <CalculatorOtsPage />,
                allowedRoles: ROLES.WORKERS
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.RESPONSIBLE,
                element: <ResponsiblePage />,
                allowedRoles: ROLES.WORKERS
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.AUDIO_OBJECTIONS,
                element: <AudioObjectionsPage />,
                allowedRoles: ROLES.WORKERS
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.SHOP,
                element: <OnlineStorePage />,
                allowedRoles: ROLES.WORKERS
            } as any,
            {
                path: APP_CONFIG.ROUTES.PRIVATE.SETTINGS,
                element: <SettingsPage />,
                allowedRoles: ROLES.ALL
            } as any,
        ]   
    }
];
