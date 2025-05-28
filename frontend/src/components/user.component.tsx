// Компонент для отображения пользователя
// Отображается в правой части шапки

import { Dropdown, Avatar } from 'antd';
import { UserOutlined, LogoutOutlined, FullscreenOutlined, ProfileOutlined, UnlockOutlined, BellOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { APP_CONFIG } from '@/config/app.config';

interface UserComponentProps {
    enterFullscreen: () => void;
    logout: () => void;
}

const UserComponent: React.FC<UserComponentProps> = ({ enterFullscreen, logout }) => {
    const navigate = useNavigate();

    const userMenu = [
        {
            key: 'profile',
            icon: <ProfileOutlined />,
            label: <span className="text-sm sm:text-base">Перейти в профиль</span>,
            onClick: () => { navigate(APP_CONFIG.ROUTES.PRIVATE.PROFILE);}
        },
        {
            type: 'divider' as const
        },
        {
            key: 'sessions',
            icon: <UnlockOutlined />,
            label: <span className="text-sm sm:text-base">Управление сессиями</span>,
            onClick: () => { navigate(APP_CONFIG.ROUTES.PRIVATE.SESSIONS);}
        },
        {
            type: 'divider' as const
        },
        {
            key: 'notifications',
            icon: <BellOutlined />,
            label: <span className="text-sm sm:text-base">Управление push-уведомлениями</span>,
            onClick: () => { navigate(APP_CONFIG.ROUTES.PRIVATE.SETTINGS)}
        },
        {
            type: 'divider' as const
        },
        {
            key: 'fullscreen',
            icon: <FullscreenOutlined />,
            label: <span className="text-sm sm:text-base">На весь экран</span>,
            onClick: enterFullscreen
        },
        {
            type: 'divider' as const
        },
        {
            key: 'logout',
            icon: <LogoutOutlined />,
            label: <span className="text-sm sm:text-base">Выйти из аккаунта</span>,
            danger: true,
            onClick: logout
        }
    ];

    return (
        <Dropdown menu={{ items: userMenu }} trigger={['click']}>
            <Avatar 
                className="cursor-pointer select-none"
                icon={<UserOutlined />}
                size="large"
            />
        </Dropdown>
    );
};

export default UserComponent;
