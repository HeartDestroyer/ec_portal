import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Spin } from 'antd';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import { publicRoutes, protectedRoutes } from '@/routes';
import { APP_CONFIG } from '@/config/app.config';

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
    );
};

export default App;
