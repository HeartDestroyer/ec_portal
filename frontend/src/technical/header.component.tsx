// Компонент header
// Отображается в верхней части страницы

import React, { memo } from 'react';
import { Button, Layout } from 'antd';
import { MenuUnfoldOutlined, MenuFoldOutlined } from '@ant-design/icons';
import { useAuth } from '@/context/auth.context';
import UserComponent from '@/components/user.component';

interface HeaderProps {
    collapsed: boolean;
    toggleSidebar: () => void;
    enterFullscreen: () => void;
    onMobileMenuOpen: boolean;
}

const Header: React.FC<HeaderProps> = memo(({ 
    collapsed,
    toggleSidebar,
    enterFullscreen,
    onMobileMenuOpen
}) => {
    const { Header: AntHeader } = Layout;
    const { user, logout } = useAuth();

    const headerStyle: React.CSSProperties = {
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 20,
        backgroundColor: 'rgba(255, 255, 255, 0.9)', height: 70, padding: '0 25px',
        borderBottom: '1px solid #e5e5e5'
    };

    return (
        <AntHeader style={headerStyle} className="flex items-center justify-between">
            <div className='flex flex-row items-center gap-3 sm:gap-5'>
                <div className= {`${onMobileMenuOpen ? 'block' : 'hidden'}`}>
                    <Button
                        type="default"
                        size='middle'
                        icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                        onClick={toggleSidebar}
                    />
                </div>
                <div className='text-2xl sm:text-3xl font-bold animate-header'>
                    {import.meta.env.VITE_APP_NAME}
                </div>
            </div>

            <div className='flex flex-row items-center gap-3'>
                <div className='hidden sm:block text-base font-medium'>
                    {!onMobileMenuOpen && user?.name}
                </div>
                <UserComponent enterFullscreen={enterFullscreen} logout={logout} />
            </div>
        </AntHeader>
    );
});

Header.displayName = 'Header';

export default Header;
