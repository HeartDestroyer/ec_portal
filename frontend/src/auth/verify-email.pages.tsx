/**
 * Страница для подтверждения email
 */

import React, { useEffect, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { authService } from "@/services/auth.service";
import { Spin } from "antd";
import { APP_CONFIG } from "@/config/app.config";

const VerifyEmailPage: React.FC = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();

    const verifyEmail = useCallback(async (token: string) => {
        try {
            await authService.verifyEmail(token);
            setTimeout(() => navigate(APP_CONFIG.ROUTES.PUBLIC.LOGIN), 3000);
        } catch (error: any) {
            console.error("Ошибка подтверждения email:", error);
        }
    }, [navigate]);

    useEffect(() => {
        const token = searchParams.get("token");
        if (!token) {
            return;
        }

        verifyEmail(token);
    }, [verifyEmail, searchParams]);

    return (
        <div className="flex flex-col items-center justify-center min-h-screen">
            <Spin size="large" />
        </div>
    );
};

export default VerifyEmailPage;
