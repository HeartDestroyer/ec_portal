import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import { useAuth } from '../context/AuthContext';
import { APP_CONFIG } from '../config/app.config';

interface ProtectedRouteProps {
    children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
    const { isAuthenticated, isLoading } = useAuth();
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

    return <>{children}</>;
}; 