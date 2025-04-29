// Компонент для отображения пользователя
// Отображается в правой части шапки

import { Dropdown, Menu, Avatar } from 'antd';
import { UserOutlined, LogoutOutlined, FullscreenOutlined } from '@ant-design/icons';
import { useAuth } from '@/context/auth.context';

interface UserComponentProps {
    enterFullscreen: () => void;
    logout: () => void;
}

const UserComponent: React.FC<UserComponentProps> = ({ enterFullscreen, logout }) => {
    const { user } = useAuth();

    const userMenu = (
        <Menu>
            <Menu.Item key="user">
                <div className="flex flex-col">
                    <span className="text-sm sm:text-base">Логин: {user?.login}</span>
                    <span className="text-sm sm:text-base">Телефон: {user?.phone}</span>
                    <span className="text-sm sm:text-base">Почта: {user?.email}</span>
                </div>
            </Menu.Item>
            <Menu.Divider />
            <Menu.Item key="fullscreen" onClick={enterFullscreen} icon={<FullscreenOutlined />}>
                <span className="text-sm sm:text-base">На весь экран</span>
            </Menu.Item>
            <Menu.Item key="logout" onClick={logout} icon={<LogoutOutlined />}>
                <span className="text-sm sm:text-base">Выйти</span>
            </Menu.Item>
        </Menu>
    );

    return (
        <Dropdown overlay={userMenu} trigger={['click']}>
            <Avatar 
                className="cursor-pointer bg-[#0D3B66] select-none"
                icon={<UserOutlined />}
                size="large"
            />
        </Dropdown>
    );
};

export default UserComponent;