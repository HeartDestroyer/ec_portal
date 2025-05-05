import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ConfigProvider, Spin, message } from 'antd';
import { AuthProvider, useAuth } from '@/context/auth.context';
import { publicRoutes, protectedRoutes } from '@/routes';
import { APP_CONFIG } from '@/config/app.config';
import ruRU from 'antd/es/locale/ru_RU';

const theme = {
    token: {
        colorPrimary: '#0D3B66',
    },
        Button: {
            boxShadow: 'none',
        },
};

interface ProtectedRouteProps {
    children: React.ReactNode;
    allowedRoles?: string[];
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
    const { isAuthenticated, isLoading, user } = useAuth();
    const location = useLocation();

    if (isLoading) {
        return (
            <div className="flex justify-center items-center h-screen">
                <Spin size="large" tip="Загрузка..." />
            </div>
        );
    }

    if (!isAuthenticated) {
        return <Navigate to={APP_CONFIG.ROUTES.PUBLIC.LOGIN} state={{ from: location }} replace />;
    }

    if (allowedRoles && (!user || !allowedRoles.includes(user.role))) {
        message.error('У вас нет доступа к этой странице');
        return <Navigate to={APP_CONFIG.ROUTES.PUBLIC.START} replace />;
    }

    return <>{children}</>;
};

const App: React.FC = () => {
    return (
        <ConfigProvider locale={ruRU} theme={theme}>
            <AuthProvider>
                <Router>
                    <Routes>
                        {publicRoutes.map((route) => (
                            <Route key={route.path} path={route.path} element={route.element} />
                        ))}
                        {protectedRoutes.map((route) => (
                            <Route
                                key={route.path}
                                path={route.path}
                                element={<ProtectedRoute allowedRoles={(route as any).allowedRoles}>{route.element}</ProtectedRoute>}
                            >
                                {route.children && route.children.map((child) => (
                                <Route
                                    key={child.index ? 'index' : child.path}
                                    index={child.index}
                                    path={child.path}
                                    element={
                                        <ProtectedRoute allowedRoles={(child as any).allowedRoles}>
                                            {child.element}
                                        </ProtectedRoute>
                                    }
                                />
                                ))}
                            </Route>
                            ))}
                    </Routes>
                </Router>
            </AuthProvider>
        </ConfigProvider>
    );
};

export default App;
