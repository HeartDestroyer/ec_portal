import React from 'react';
import { Layout, Menu } from 'antd';
import { useAuth } from '@/context/AuthContext';
import LogoutButton from '@/authorization/LogoutButton';

const { Header, Content } = Layout;

const Dashboard: React.FC = () => {
    const { logout } = useAuth();

    return (
        <Layout className="min-h-screen">
            <Header className="flex items-center justify-between bg-white px-6">
                <div className="text-xl font-bold">ЭЦ-портал</div>
                <div className="flex items-center gap-4">
                    <LogoutButton onLogout={logout} />
                </div>
            </Header>
            <Content className="p-6">
                <div className="bg-white p-6 rounded-lg shadow">
                    <h1 className="text-2xl font-bold mb-4">Добро пожаловать в ЭЦ-портал</h1>
                    <p>Здесь будет основное содержимое вашего приложения.</p>
                </div>
            </Content>
        </Layout>
    );
};

export default Dashboard; 