/**
 * Маршруты для авторизации
 * Содержит маршруты для авторизации
 */
import { lazy } from 'react';
import { RouteObject } from 'react-router-dom';
import { APP_CONFIG } from '../config/app.config';
import { ROLES } from '@/config/roles.config';

import LoginForm from '../auth/login.form'; /** Страница для авторизации */
import RegisterForm from '../auth/register.form'; /** Страница для регистрации */
import ResetPassword from '../auth/reset-password.form'; /** Страница для сброса пароля */
import NewPassword from '../auth/password-recovery.form'; /** Страница для сброса пароля */
import VerifyEmailPage from '../auth/verify-email.pages'; /** Страница для подтверждения email */
import NotFound from '../technical/404.component'; /** Страницы для 404 ошибки */
import HomeRoute from '../components/home.route'; /** Домашняя страница */

const DashboardLayout = lazy(() => import('@/technical/layout.page')); /** Страница для шаблона */
const AdminPanelPage = lazy(() => import('../admin_panel/admin_panel.page')); /** Страница для админ панели */
const DashboardPage = lazy(() => import('../components/dashboard.page')); /** Страница для главного экрана */
const ProfilePage = lazy(() => import('../profile/components/info.page')); /** Страница для профиля пользователя */
const AchievementsPage = lazy(() => import('../profile/components/achievements.page')); /** Страница для достижений */
const LetterPage = lazy(() => import('../profile/components/letter.page')); /** Страница для шаблонов письма */
const EmployeesPage = lazy(() => import('../organizations/components/employees.page')); /** Страница для сотрудников */
const CompanyStructurePage = lazy(() => import('../organizations/components/company_structure.page')); /** Страница для структуры компании */
const VideoLessonsPage = lazy(() => import('../video_lessons/components/video_lessons.page')); /** Страница для видеоуроков новичков */
const LeaderLessonsPage = lazy(() => import('../video_lessons/components/leader.page')); /** Страница для видеоуроков лидеров */
const MasterClassPage = lazy(() => import('../video_lessons/components/master_class.page')); /** Страница для мастер класса */
const CheckListPage = lazy(() => import('../video_lessons/components/check_list.page')); /** Страница для чек листа */
const HrPage = lazy(() => import('../candidates/components/hr.page')); /** Страница для HR тестирования */
const PresentationPage = lazy(() => import('../presentation/components/presentation.page')); /** Страница для презентации партнеров */
const ObjectionsPage = lazy(() => import('../objection/components/objection.page')); /** Страница для возражений о неоплате */
const CustomerReviewsPage = lazy(() => import('../tools_and_assistants/components/customer_reviews.page')); /** Страница для отзывов клиентов */
const CalculatorOtsPage = lazy(() => import('../tools_and_assistants/components/calculator.page')); /** Страница для калькулятора ОТС */
const ResponsiblePage = lazy(() => import('../tools_and_assistants/components/responsible.page')); /** Страницы для справочника */
const AudioObjectionsPage = lazy(() => import('../tools_and_assistants/components/audio_objections.page')); /** Страница для аудио возражений о неоплате */
const OnlineStorePage = lazy(() => import('../online_store/components/online_store.page')); /** Страница для онлайн магазина */
const SettingsPage = lazy(() => import('../settings/components/settings.page')); /** Страница для настроек */
const SessionsPage = lazy(() => import('../components/sessions.page')); /** Страница для сессий */

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
        path: APP_CONFIG.ROUTES.PUBLIC.PASSWORD_RECOVERY,
        element: <NewPassword />
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
            {
                path: APP_CONFIG.ROUTES.PRIVATE.SESSIONS,
                element: <SessionsPage />,
                allowedRoles: ROLES.ALL
            } as any,
        ]   
    }
];
