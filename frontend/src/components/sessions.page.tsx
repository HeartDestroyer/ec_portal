import React, { useEffect, useState, useCallback } from 'react';
import { Table, Button, Modal, Input, Select } from 'antd';
import { sessionService } from '@/services/session.service';
import type { Session } from '@/types/session.types';
import type { SessionsPage, SessionFilter } from '@/types/session.types';
import { useAuth } from '@/context/auth.context';
import { SearchOutlined } from '@ant-design/icons';
import { ROLES } from '@/config/roles.config';
import type { Breakpoint } from 'antd/es/_util/responsiveObserver';


const { Option } = Select;

const SessionsPage: React.FC = () => {
    const { user } = useAuth();
    const [sessionsData, setSessionsData] = useState<SessionsPage>({
        total: 0,
        page: 1,
        page_size: 12,
        sessions: []
    });
    const [filters, setFilters] = useState<SessionFilter>({
        page: 1,
        page_size: 12,
        user_name: '',
        is_active: undefined
    });
    const [loading, setLoading] = useState<boolean>(false);
    const [modalVisible, setModalVisible] = useState<boolean>(false);

    const [sessionId, setSessionId] = useState<string | null>(null);
    const [sessionName, setSessionName] = useState<string | null>(null);

    /** Получение сессий */
    const fetchSessions = useCallback(async () => {
        try {
            setLoading(true);
            const data = await sessionService.getActiveSessions(filters);
            setSessionsData(data);
        } catch (error) {
            console.error('Ошибка при получении сессий:', error);
        } finally {
            setLoading(false);
        }
    }, [filters]);

    useEffect(() => {
        fetchSessions();
    }, [fetchSessions]);

    /** Открытие модального окна для завершения сессии */
    const handleTerminateSession = useCallback(async (sessionId: string, userName: string) => {
        setSessionId(sessionId);
        setSessionName(userName);
        setModalVisible(true);
    }, []);

    /** Завершение конкретной сессии */
    const confirmTerminateSession = useCallback(async () => {
        if (!sessionId) return;

        try {
            await sessionService.terminateSession(sessionId);
            fetchSessions();
        } catch (error) {
            console.error('Ошибка при завершении сессии:', error);
        } finally {
            setModalVisible(false);
            setSessionId(null);
        }
    }, [sessionId, fetchSessions]);

    /** Завершение всех других сессий */
    const handleTerminateOtherSessions = useCallback(async () => {
        try {
            await sessionService.terminateOtherSessions();
            fetchSessions();
        } catch (error) {
            console.error('Ошибка при завершении других сессий:', error);
        }
    }, [fetchSessions]);

    /** Обработчик изменения фильтра по имени пользователя */
    const handleUserNameChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        setFilters(prev => ({ ...prev, user_name: e.target.value }));
    }, []);

    /** Обработчик изменения фильтра по статусу */
    const handleStatusChange = useCallback((value: 'all' | 'true' | 'false') => {
        setFilters(prev => ({
            ...prev,
            is_active: value === 'all' ? undefined : value === 'true'
        }));
    }, []);

    /** Обработчик закрытия модального окна */
    const handleModalClose = useCallback(() => {
        setModalVisible(false);
    }, []);

    /** Колонки таблицы */
    const tableColumns = useCallback(() => [
        {
            title: 'Пользователь',
            dataIndex: 'user_name',
            key: 'user_name',
            responsive: ['xs', 'sm', 'md', 'lg', 'xl'] as Breakpoint[],
            width: 130,
            fixed: 'left' as const,
            render: (text: string) => <span>{text}</span>
        },
        {
            title: 'Устройство',
            dataIndex: 'device',
            key: 'device',
            responsive: ['lg', 'xl'] as Breakpoint[],
            width: 170,
            render: (_: any, record: Session) => (
                <span>{record.browser} • {record.os}</span>
            )
        },
        {
            title: 'IP-адрес',
            dataIndex: 'ip_address',
            key: 'ip_address',
            responsive: ['lg', 'xl'] as Breakpoint[],
            width: 100,
            render: (text: string) => <span>{text}</span>
        },
        {
            title: 'Местоположение',
            dataIndex: 'location',
            key: 'location',
            responsive: ['xs', 'sm', 'md', 'lg', 'xl'] as Breakpoint[],
            width: 200,
            render: (text: string) => <span>{text}</span>
        },
        {
            title: 'Дата создания',
            dataIndex: 'created_at',
            key: 'created_at',
            responsive: ['xs', 'sm', 'md', 'lg', 'xl'] as Breakpoint[],
            width: 160,
            render: (text: string) => new Date(text).toLocaleString(),
        },
        {
            title: 'Последняя активность',
            dataIndex: 'last_activity',
            key: 'last_activity',
            responsive: ['xs', 'sm', 'md', 'lg', 'xl'] as Breakpoint[],
            width: 160,
            render: (text: string) => new Date(text).toLocaleString(),
        },
        {
            title: 'Статус',
            dataIndex: 'is_active',
            key: 'is_active',
            responsive: ['xs', 'sm', 'md', 'lg', 'xl'] as Breakpoint[],
            width: 90,
            render: (isActive: boolean) => (
                <span style={{ color: isActive ? 'green' : 'red' }}>{isActive ? 'Активна' : 'Неактивна'}</span>
            )
        },
        {
            title: 'Действия',
            key: 'actions',
            responsive: ['xs', 'sm', 'md', 'lg', 'xl'] as Breakpoint[],
            width: 90,
            render: (_: any, record: Session) => (
                <>
                    {!record.is_current && record.is_active && (
                        <Button 
                            danger 
                            size="small"
                            type="link"
                            className='!p-0'
                            onClick={() => handleTerminateSession(record.id, record.user_name)}
                        >
                            Завершить
                        </Button>
                    )}

                    {record.is_current && (
                        <span>Текущая</span>
                    )}

                    {!record.is_current && !record.is_active && (
                        <span> - </span>
                    )}
                </>
            ),
        },
    ], [handleTerminateSession]);

    return (
        <div className="pb-4">
            <h1>Управление сессиями</h1>
            <p className="text-base">Управление активными сессиями пользователя</p>
            
            <div className='flex flex-col md:flex-row gap-3 mb-4'>
                <div className='flex flex-row gap-3' style={{ width: '100%' }}>
                    <Select
                        value={filters.is_active === undefined ? 'all' : filters.is_active ? 'true' : 'false'}
                        onChange={handleStatusChange}
                        style={{ width: 200 }}
                    >
                        <Option value="all">Все сессии</Option>
                        <Option value="true">Активные</Option>
                        <Option value="false">Неактивные</Option>
                    </Select>

                    {ROLES.ADMIN.includes(user?.role as 'superadmin' | 'admin') && (
                        <Input
                            placeholder="Поиск по имени пользователя"
                            prefix={<SearchOutlined />}
                            value={filters.user_name}
                            onChange={handleUserNameChange}
                        />
                    )}
                </div>

                <Button 
                    type="primary" 
                    danger 
                    onClick={handleTerminateOtherSessions}
                    size="middle"
                >
                    Завершить все мои сессии, кроме текущей
                </Button>
            </div>
                
            <div style={{ width: '100%', overflowX: 'auto' }}>
                <Table 
                    className='custom-scrollbar'
                    columns={tableColumns()} 
                    dataSource={sessionsData.sessions} 
                    loading={loading}
                    rowKey="id"
                    size="middle"
                    bordered={true}
                    pagination={{
                        total: sessionsData.total,
                        current: sessionsData.page,
                        pageSize: filters.page_size,
                        onChange: (page, pageSize) => {
                            setFilters(prev => ({ ...prev, page, page_size: pageSize }));
                            fetchSessions;
                        },
                        showSizeChanger: true,
                        showTotal: (total) => `Общее количество сессий: ${total} `
                    }}
                    scroll={{ x: 900 }}
                />
            </div>

            <Modal
                title={<span className='text-lg'>Подтверждение</span>}
                open={modalVisible}
                onOk={confirmTerminateSession}
                onCancel={handleModalClose}
                okText='Да'
                cancelText='Нет'
            >
                <span className='text-sm sm:text-base'>Вы уверены, что хотите завершить сессию {sessionName}?</span>
            </Modal>
        </div>
    );
};

export default SessionsPage;
