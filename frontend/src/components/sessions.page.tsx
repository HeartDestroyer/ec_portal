import React, { useEffect, useState } from 'react';
import { Table, Button, Space, Modal } from 'antd';
import { authService } from '@/services/auth.service';
import { Session } from '@/types/auth.types';
import { showMessage } from '@/utils/show.message';
import { useAuth } from '@/context/auth.context';

const SessionsPage: React.FC = () => {
    const { user } = useAuth();
    const [sessions, setSessions] = useState<Session[]>([]);
    const [loading, setLoading] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

    const fetchSessions = async () => {
        try {
            setLoading(true);
            const data = await authService.getActiveSessions() as Session[];
            setSessions(data);
        } catch (error) {
            console.error('Ошибка при получении сессий:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSessions();
    }, []);

    const handleTerminateSession = async (sessionId: string) => {
        setSelectedSessionId(sessionId);
        setModalVisible(true);
    };

    const confirmTerminateSession = async () => {
        if (!selectedSessionId) return;

        try {
            await authService.terminateSession(selectedSessionId);
            fetchSessions();
        } catch (error) {
            console.error('Ошибка при завершении сессии:', error);
        } finally {
            setModalVisible(false);
            setSelectedSessionId(null);
        }
    };

    const handleTerminateOtherSessions = async () => {
        try {
            await authService.terminateOtherSessions();
            fetchSessions();
        } catch (error) {
            console.error('Ошибка при завершении других сессий:', error);
        }
    };

    const columns = [
        {
            title: 'Устройство',
            dataIndex: 'device',
            key: 'device',
        },
        {
            title: 'Браузер',
            dataIndex: 'browser',
            key: 'browser',
        },
        {
            title: 'IP-адрес',
            dataIndex: 'ip_address',
            key: 'ip_address',
        },
        {
            title: 'Последняя активность',
            dataIndex: 'last_activity',
            key: 'last_activity',
            render: (text: string) => new Date(text).toLocaleString(),
        },
        {
            title: 'Действия',
            key: 'actions',
            render: (_: any, record: Session) => (
                <Space>
                    {!record.is_current && (
                        <Button 
                            danger 
                            size="small"
                            type="link"
                            onClick={() => handleTerminateSession(record.id)}
                        >
                            Завершить
                        </Button>
                    )}
                    {record.is_current && <span>Текущая сессия</span>}
                </Space>
            ),
        },
    ];

    return (
        <div className="pb-4">
            <h1>Управление сессиями</h1>
            <p className="text-base">Управление активными сессиями пользователя {user?.name}</p>

            <Button 
                type="primary" 
                danger 
                onClick={handleTerminateOtherSessions}
                size="middle"
                className='!mb-4'
            >
                Завершить все другие сессии
            </Button>

            <Table 
                columns={columns} 
                dataSource={sessions} 
                loading={loading}
                rowKey="id"
                size="middle"
                bordered={true}
            />
            <Modal
                title="Подтверждение"
                open={modalVisible}
                onOk={confirmTerminateSession}
                onCancel={() => setModalVisible(false)}
                okText="Да"
                cancelText="Нет"
            >
                <p>Вы уверены, что хотите завершить эту сессию?</p>
            </Modal>
        </div>
    );
};

export default SessionsPage;
