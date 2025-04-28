import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, Spin } from 'antd';
import { AuthProvider, useAuth } from '@/context/auth.context';
import { publicRoutes, protectedRoutes } from '@/routes';
import { APP_CONFIG } from '@/config/app.config';
import './index.css';
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
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
    const { isAuthenticated, isLoading } = useAuth();

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
                                element={<ProtectedRoute>{route.element}</ProtectedRoute>}
                            />
                        ))}
                    </Routes>
                </Router>
            </AuthProvider>
        </ConfigProvider>
    );
};

export default App;
