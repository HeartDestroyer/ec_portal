// Страница сборки

import React, { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Layout } from 'antd';
import Header from '@/technical/header.component';
import SidebarMenu from '@/technical/menu.component';
import { motion, AnimatePresence } from 'framer-motion';

const { Content } = Layout;

const DashboardLayout: React.FC = () => {
    const [collapsed, setCollapsed] = useState<boolean>(false); // Состояние меню
    const [isFullscreen, setIsFullscreen] = useState<boolean>(false); // Состояние полноэкранного режима
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
            
            <Layout className="pt-20 !flex-row">
                <SidebarMenu
                    selectedPath={location.pathname}
                    collapsed={collapsed}
                    closeSidebar={() => setCollapsed(true)}
                    toggleSidebar={() => setCollapsed(!collapsed)}
                    onMobileMenuOpen={mobileMenuOpen}
                />
                
                <AnimatePresence mode="wait">
                    <motion.div
                        key={location.pathname}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        transition={{ duration: 0.2 }}
                        className='flex-1 transition-all duration-300'
                    >
                        <Content className="p-6">
                            <div className="p-4 bg-white rounded-lg shadow-md ">
                                <Outlet />
                            </div>
                        </Content>
                    </motion.div>
                </AnimatePresence>
            </Layout>
        </Layout>
    );
};

export default DashboardLayout;
