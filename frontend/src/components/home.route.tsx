/** Стартовая страница */

import React from "react";
import { useAuth } from "@/context/auth.context";
import { Spin } from "antd";
import HomePage from "@/components/home.components";
import { Navigate } from "react-router-dom";
import { APP_CONFIG } from "@/config/app.config";

const HomeRoute: React.FC = () => {
    const { isAuthenticated, isLoading } = useAuth();

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen">
                <Spin size="large" />
            </div>
        );
    }

    if (isAuthenticated) { 
        return <Navigate to={APP_CONFIG.ROUTES.PRIVATE.START} replace />
    };

    return <HomePage />;
};

export default HomeRoute;
