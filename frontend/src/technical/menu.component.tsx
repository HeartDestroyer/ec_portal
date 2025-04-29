// frontend/src/components/layout/SidebarMenu.tsx

import React, { memo, useCallback, useMemo, useState } from 'react';
import { Menu, Button, Badge } from 'antd';
import { DashboardOutlined, UserOutlined, ThunderboltOutlined, 
    ShoppingOutlined, StarOutlined, SettingOutlined, TeamOutlined, 
    VideoCameraOutlined, LeftOutlined, RightOutlined, BookOutlined, ApartmentOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/auth.context';
import { cache } from '@/services/cache.service';
import { motion } from 'framer-motion';

const { SubMenu } = Menu;

interface SidebarMenuProps {
    selectedPath: string;
    collapsed: boolean;
    closeSidebar: () => void;
    toggleSidebar: () => void;
    onMobileMenuOpen: boolean;
}

type RoleType = 'superadmin' | 'admin' | 'leader' | 'employee';
type DepartmentType = 1 | 7;

interface MenuItem {
    key: string;
    icon: React.ReactNode;
    label: string;
    roles?: RoleType[];
    departments?: DepartmentType[];
    children?: MenuItem[];
    badge?: number;
}

const ROLES = {
    SUPERADMIN: ['superadmin'] as RoleType[],
    ADMIN: ['superadmin', 'admin'] as RoleType[],
    LEADER: ['superadmin', 'admin', 'leader'] as RoleType[],
    WORKERS: ['superadmin', 'admin', 'leader', 'employee'] as RoleType[],
} as const;

const DEPARTMENTS = {
    HR: [1] as DepartmentType[],
    OTS: [7] as DepartmentType[],
} as const;

const NO_NAVIGATE_KEYS = ['cache_reset'];

/**
 * Конфигурация меню
 */
const getMenuItems = (): MenuItem[] => [
    {
        key: '/admin',
        icon: <SettingOutlined />,
        label: 'Администратор',
        roles: ROLES.ADMIN
    },
    {
        key: '/',
        icon: <DashboardOutlined />,
        label: 'Главная'
    },
    {
        key: 'ProfileSetting',
        icon: <UserOutlined />,
        label: 'Профиль',
        children: [
            {
                key: '/profile',
                icon: <ThunderboltOutlined />,
                label: 'Информация'
            },
            {
                key: '/letter',
                icon: <ThunderboltOutlined />,
                label: 'Шаблоны писем',
                roles: ROLES.WORKERS,
                badge: 5
            },
            {
                key: '/achievement',
                icon: <ThunderboltOutlined />,
                label: 'Достижения',
                roles: ROLES.WORKERS,
                badge: 3
            }
        ]
    },
    {
        key: 'Organization',
        icon: <ApartmentOutlined />,
        label: 'Организация',
        roles: ROLES.WORKERS,
        children: [
            {
                key: '/groups',
                icon: <ThunderboltOutlined />,
                label: 'Сотрудники'
            },
            {
                key: '/organization',
                icon: <ThunderboltOutlined />,
                label: 'Структура'
            }
        ]
    },
    {
        key: 'Training',
        icon: <VideoCameraOutlined />,
        label: 'Обучение',
        roles: ROLES.WORKERS,
        children: [
            {
                key: '/education',
                icon: <ThunderboltOutlined />,
                label: 'Руководители',
                roles: ROLES.LEADER,
            },
            {
                key: '/masterclass',
                icon: <ThunderboltOutlined />,
                label: 'Мастер классы'
            },
            {
                key: '/lessons',
                icon: <ThunderboltOutlined />,
                label: 'Видеоуроки'
            },
            {
                key: '/checklist',
                icon: <ThunderboltOutlined />,
                label: 'Чек-лист новичка'
            },                
        ]
    },
    {
        key: '/candidates',
        icon: <StarOutlined />,
        label: 'HR-тестирование'
    },
    {
        key: '/presentation',
        icon: <StarOutlined />,
        label: 'Презентация'
    },
    {
        key: '/objections',
        icon: <StarOutlined />,
        label: 'Возражения'
    },
    {
        key: 'Assistant',
        icon: <StarOutlined />,
        label: 'Инструменты',
        roles: ROLES.WORKERS,
        children: [
            {
                key: '/reviews',
                icon: <ThunderboltOutlined />,
                label: 'Отзывы клиентов',
            },
            {
                key: '/calculator',
                icon: <ThunderboltOutlined />,
                label: 'Калькулятор ОТС'
            },
            {
                key: '/responsible',
                icon: <ThunderboltOutlined />,
                label: 'Справочник'
            },
            {
                key: '/audio',
                icon: <ThunderboltOutlined />,
                label: 'Аудио-возражения'
            },                
        ]
    },
    {
        key: '/shop',
        icon: <ShoppingOutlined />,
        label: 'Магазин'
    },
    {
        key: '/settings',
        icon: <SettingOutlined />,
        label: 'Настройки'
    },
];

const SidebarMenu: React.FC<SidebarMenuProps> = memo(({ 
    selectedPath, 
    collapsed, 
    closeSidebar, 
    toggleSidebar,
    onMobileMenuOpen
}) => {
    const navigate = useNavigate();
    const location = useLocation();
    const { user } = useAuth();

    /** Фильтрация пунктов меню по ролям и департаментам */
    const filteredMenuItems = useMemo(() => {
        const filterMenuItem = (item: MenuItem): boolean => {
            const hasRequiredRole = !item.roles || 
                (user?.role && item.roles.includes(user.role as RoleType));
            const hasRequiredDepartment = !item.departments || 
                (user?.department_id && item.departments.includes(user.department_id as DepartmentType));
            
            return hasRequiredRole && hasRequiredDepartment;
        };

        const filterMenuItems = (items: MenuItem[]): MenuItem[] => {
            return items.reduce<MenuItem[]>((acc, item) => {
                if (!filterMenuItem(item)) return acc;

                if (item.children) {
                    const filteredChildren = filterMenuItems(item.children);
                    if (filteredChildren.length > 0) {
                        acc.push({ ...item, children: filteredChildren });
                    }
                } else {
                    acc.push(item);
                }
                return acc;
            }, []);
        };

        return filterMenuItems(getMenuItems());
    }, [user]);

    /** Обработчики */
    const onMenuSelect = useCallback(
        (e: { key: string }) => {
            if (!NO_NAVIGATE_KEYS.includes(e.key)) {
                navigate(e.key);
                if (window.innerWidth < 1024) closeSidebar();
            }
        },
        [closeSidebar, navigate]
    );

    /** Сброс кэша */
    const handleCacheReset = useCallback(async () => {
        try {
            await cache.clear();
        } catch (error) {
            console.error('Ошибка при сбросе кэша:', error);
        }
    }, []);
    
    /** Рендер пункта меню */
    const renderMenuItem = (item: MenuItem) => {
        if (item.children) {
            return (
                <SubMenu key={item.key} icon={item.icon} title={item.label}>
                    {item.children.map(child => renderMenuItem(child))}
                </SubMenu>
            );
        }
        
        return (
            <Menu.Item
                key={item.key}
                icon={
                    item.icon
                }
                className='flex items-center'
            >
                {item.label}
                <Badge count={item?.badge} offset={[10, 0]} />
            </Menu.Item>
        );
    };

    return (
        <>
            <div className={`
                ${onMobileMenuOpen ? 'fixed top-0 left-0 bottom-0 z-40' : 'relative translate-x-0'}
                ${collapsed ? '-translate-x-full' : 'translate-x-0'}
                transition-transform transform shadow-lg
            `}>

                {/* Кнопка сворачивания/разворачивания меню */}
                <div className= {`
                    ${onMobileMenuOpen ? 'hidden' : 'block'} 
                    absolute top-3 -right-4 z-50 bg-white rounded-full
                `}>
                    <Button
                        type="default"
                        size='middle'
                        icon={collapsed ? <RightOutlined /> : <LeftOutlined />}
                        onClick={toggleSidebar}
                        className='!rounded-full'
                    />
                </div>

                {/* Меню */}
                <div className={`
                    ${collapsed ? '!w-20' : '!w-64'}
                    ${onMobileMenuOpen ? 'h-full' : 'h-[calc(100vh-80px)]'}
                    custom-scrollbar custom-scrollbar-menu
                    z-40 sticky top-20 transition-all duration-300 bg-white
                `}>
                    <Menu
                        className='h-full !pt-2 font-medium !text-base'
                        selectedKeys={[selectedPath]}
                        defaultOpenKeys={[location.pathname.split('/')[2]]}
                        mode="inline"
                        theme="light"
                        inlineCollapsed={collapsed}
                        onClick={onMenuSelect}
                    >
                        {filteredMenuItems.map(renderMenuItem)}

                        {/* Сброс кэша */}
                        {user?.role && ROLES.WORKERS.includes(user.role as RoleType) && (
                            <Menu.Item 
                                key="cache_reset" 
                                icon={<ThunderboltOutlined />} 
                                onClick={handleCacheReset}
                                className="mt-auto"
                            >
                                Сбросить кэш
                            </Menu.Item>
                        )}
                    </Menu>
                </div>
            </div>

            {/* Overlay */}
            {!collapsed && (
                <motion.div 
                    className={`
                        ${onMobileMenuOpen ? '' : 'hidden'}
                        fixed inset-0 bg-black/50 backdrop-blur-sm z-30 md:hidden
                    `}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={closeSidebar}
                />
            )}
        </>
    );
});

SidebarMenu.displayName = 'SidebarMenu';

export default SidebarMenu;
