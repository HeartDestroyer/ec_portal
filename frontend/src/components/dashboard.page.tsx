// Компонент для отображения главной страницы

import React from 'react';
import { useAuth } from '@/context/auth.context';
import { APP_CONFIG } from '@/config/app.config';

const Dashboard: React.FC = () => {
    const { user } = useAuth();
    
    return (
        <div className="pb-4">
            <h1>Добро пожаловать, {user?.name}</h1>
            <p className='text-base'>Ваш персональный {APP_CONFIG.NAME} для работы и обучения</p>
        </div>
    );
};

export default Dashboard;
