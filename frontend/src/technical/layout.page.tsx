// Страница сборки

import React, { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Layout } from 'antd';
import Header from '@/technical/header.component';
import SidebarMenu from '@/technical/menu.component';
import { motion, AnimatePresence } from 'framer-motion';
import Breadcrumbs from '@/technical/breadcrumbs';

const { Content } = Layout;

const DashboardLayout: React.FC = () => {
    const [collapsed, setCollapsed] = useState<boolean>(false); // Состояние меню
    const [, setIsFullscreen] = useState<boolean>(false); // Состояние полноэкранного режима
    const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false); // Состояние мобильного меню
    const location = useLocation();

    /** Управление полноэкранным режимом */
    const enterFullscreen = () => {
        if (document.documentElement.requestFullscreen) {
            document.documentElement.requestFullscreen();
            setIsFullscreen(true);
        }
    };

    /** Адаптивное поведение бокового меню (десктоп) */
    useEffect(() => {
        const handleResize = () => {
            if (window.innerWidth < 1280) setCollapsed(true);
            else setCollapsed(false); 
        };

        window.addEventListener('resize', handleResize);
        handleResize();

        return () => window.removeEventListener('resize', handleResize);
    }, []);

    /** Скрытие мобильного меню при изменении размера окна */
    useEffect(() => {
        const handleResize = () => {
            if (window.innerWidth <= 767) setMobileMenuOpen(true);
            else setMobileMenuOpen(false);
        };
        window.addEventListener('resize', handleResize);
        handleResize();

        return () => window.removeEventListener('resize', handleResize);
    }, []);

    return (
        <Layout className="min-h-screen">
            <Header 
                collapsed={collapsed}
                toggleSidebar={() => setCollapsed(!collapsed)}
                enterFullscreen={enterFullscreen}
                onMobileMenuOpen={mobileMenuOpen}
            />
            
            <Layout className="!pt-[70px] !flex-row !bg-white">
                <SidebarMenu
                    selectedPath={location.pathname}
                    collapsed={collapsed}
                    closeSidebar={() => setCollapsed(true)}
                    toggleSidebar={() => setCollapsed(!collapsed)}
                    onMobileMenuOpen={mobileMenuOpen}
                />
                <Content className="p-5" style={{ width: '100%' }}>
                    <Breadcrumbs />
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={location.pathname}
                            initial={{ opacity: 0, y: 30 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -30 }}
                            transition={{ duration: 0.2 }}
                        >
                            <Outlet />
                        </motion.div>
                    </AnimatePresence>
                </Content>
            </Layout>
        </Layout>
    );
};

export default DashboardLayout;
