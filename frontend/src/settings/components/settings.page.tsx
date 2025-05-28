import React from 'react';
import NotificationManager from '@/notification/notification.manager';

const SettingsPage: React.FC = () => {

    return (
        <div className="pb-4">
            <h1>Настройки аккаунта</h1>
            <p className='text-base'>Здесь вы можете просматривать и редактировать свои настройки</p>

            <NotificationManager />
        </div>
    );
};
    
export default SettingsPage;
