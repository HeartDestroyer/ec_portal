/** Стартовая страница */

import React from "react";
import { useAuth } from "@/context/auth.context";
import { Spin } from "antd";
import HomePage from "@/components/home.components";
import Dashboard from "@/components/dashboard.components";

const HomeRoute: React.FC = () => {
    const { isAuthenticated, isLoading } = useAuth();

    if (isLoading) {
        <div className="flex flex-col items-center justify-center min-h-screen">
            <Spin size="large" />
        </div>
    }

    return isAuthenticated ? <Dashboard /> : <HomePage />;
};

export default HomeRoute;
