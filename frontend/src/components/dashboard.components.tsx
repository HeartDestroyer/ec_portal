// 

import React from 'react';
import { useAuth } from '@/context/auth.context';
import { APP_CONFIG } from '@/config/app.config';

const Dashboard: React.FC = () => {
    const { user } = useAuth();

    return (
        <div className="space-y-6">
            <div className="pb-4">
                <h1 className="text-2xl font-bold">
                    Добро пожаловать, {user?.name} на {APP_CONFIG.NAME}
                </h1>
                <p className="text-base">
                    Ваш персональный портал для работы и обучения
                </p>
            </div>                
        </div>
    );
};

export default Dashboard;
