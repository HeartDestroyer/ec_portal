import React, { useState, useEffect } from 'react';
import { Card, Button, Form, Input, Select, Tabs, Statistic, Row, Col, message, Typography, Space, Divider, Alert } from 'antd';
import { BellOutlined, SendOutlined, UserOutlined, TeamOutlined, BarChartOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { notificationService } from '../services/notification.service';
import { User, NotificationStats } from '../types/notification.types';  
import { useAuth } from '@/context/auth.context';

const { TextArea } = Input;
const { Option } = Select;


const NotificationManager: React.FC = () => {
    const { user } = useAuth();
    const [isInitialized, setIsInitialized] = useState(false);
    const [permissionStatus, setPermissionStatus] = useState<NotificationPermission>('default');
    const [stats, setStats] = useState<NotificationStats | null>(null);
    const [loading, setLoading] = useState(false);
    const [users] = useState<User[]>([
        { id: 'd53a5d47-7048-471b-830a-e80ae96b4b29', name: 'Каримов Ильнар', email: 'Ilnar_K@exp-cr.ru' },
    ]);

    const [singleForm] = Form.useForm();
    const [bulkForm] = Form.useForm();

    useEffect(() => {
        initializeNotifications();
        loadStats();
    }, []);

    /** Инициализация системы уведомлений */
    const initializeNotifications = async () => {
        try {
            const initialized = await notificationService.init();
            setIsInitialized(initialized);
            
            if (initialized) {
                await checkPermissionStatus();
                console.log('Система уведомлений инициализирована');
            } else {
                console.error('Не удалось инициализировать систему уведомлений');
            }
        } catch (error) {
            console.error('Ошибка инициализации системы уведомлений:', error);
        }
    };

    /** Проверка разрешений */
    const checkPermissionStatus = async () => {
        try {
            const permission = await notificationService.requestPermission();
            setPermissionStatus(permission);
        } catch (error) {
            console.error('Ошибка проверки разрешений:', error);
        }
    };

    /** Загрузка статистики */
    const loadStats = async () => {
        try {
            const statsData = await notificationService.getStats();
            setStats(statsData);
        } catch (error) {
            console.error('Ошибка загрузки статистики:', error);
        }
    };

    /** Отправка одиночного уведомления */
    const handleSendSingle = async (values: any) => {
        setLoading(true);
        try {
            const success = await notificationService.sendNotification({
                user_id: values.user_id,
                title: values.title,
                message: values.message,
                category: values.category,
                payload: values.payload ? JSON.parse(values.payload) : undefined
            });

            if (success) {
                message.success('Уведомление отправлено успешно');
                singleForm.resetFields();
                await loadStats();
            } else {
                message.error('Не удалось отправить уведомление');
            }
        } catch (error) {
            console.error('Ошибка отправки:', error);
            message.error('Ошибка при отправке уведомления');
        } finally {
            setLoading(false);
        }
    };

    /** Отправка массового уведомления */
    const handleSendBulk = async (values: any) => {
        setLoading(true);
        try {
            const result = await notificationService.sendBulkNotification({
                user_ids: values.user_ids.map((id: string) => parseInt(id)),
                title: values.title,
                message: values.message,
                category: values.category,
                payload: values.payload ? JSON.parse(values.payload) : undefined
            });

            message.success(
                `Массовая отправка завершена: отправлено ${result.sent}, не удалось ${result.failed}, нет подписки ${result.no_subscription}`
            );
            bulkForm.resetFields();
            await loadStats();
        } catch (error) {
            console.error('Ошибка массовой отправки:', error);
            message.error('Ошибка при массовой отправке уведомлений');
        } finally {
            setLoading(false);
        }
    };

    /** Подписка на уведомления */
    const handleSubscribe = async () => {
        try {
            // Для демонстрации используем ID первого пользователя
            const success = await notificationService.subscribeUser((users[0].id));
            if (success) {
                message.success('Подписка на уведомления активирована');
                await loadStats();
            } else {
                message.error('Не удалось подписаться на уведомления');
            }
        } catch (error) {
            console.error('Ошибка подписки:', error);
            message.error('Ошибка при подписке на уведомления');
        }
    };

    /** Рендер разрешения */
    const renderPermissionAlert = () => {
        if (permissionStatus === 'granted') {
            return (
                <Alert
                    className='!m-0 !p-3'
                    message={<span className='text-base sm:text-lg !font-medium'>Разрешения предоставлены</span>}
                    description={<span className='text-sm sm:text-base'>Push-уведомления разрешены в браузере</span>}
                    type="success"
                    icon={<CheckCircleOutlined />}
                    showIcon
                />
            );
        } else if (permissionStatus === 'denied') {
            return (
                <Alert
                    className='!m-0 !p-3 !text-sm'
                    message={<span className='text-base sm:text-lg !font-medium'>Разрешения отклонены</span>}
                    description={<span className='text-sm sm:text-base'>Push-уведомления заблокированы в браузере. Разрешите уведомления в настройках браузера</span>}
                    type="error"
                    icon={<CloseCircleOutlined />}
                    showIcon
                />
            );
        } else {
            return (
                <Alert
                    className='!m-0 !p-3 !text-sm'
                    message={<span className='text-base sm:text-lg !font-medium'>Требуется разрешение</span>}
                    description={<span className='text-sm sm:text-base'>Для работы push-уведомлений необходимо разрешение браузера</span>}
                    type="warning"
                    action={
                        <Button type='primary' size="middle" onClick={checkPermissionStatus}>
                            Запросить разрешение
                        </Button>
                    }
                    showIcon
                />
            );
        }
    };

    /** Табы */
    const tabItems = [
        {
            key: 'single',
            label: (
                <span><UserOutlined /> Одиночное уведомление</span>
            ),
            children: (
                <Card>
                    <Form
                        form={singleForm}
                        layout="vertical"
                        onFinish={handleSendSingle}
                    >
                        <Form.Item
                            name="user_id"
                            label="Получатель"
                            rules={[{ required: true, message: 'Выберите получателя' }]}
                        >
                            <Select placeholder="Выберите пользователя">
                                {users.map(user => (
                                    <Option key={user.id} value={user.id}>
                                        {user.name} ({user.email})
                                    </Option>
                                ))}
                            </Select>
                        </Form.Item>

                        <Form.Item
                            name="title"
                            label="Заголовок"
                            rules={[{ required: true, message: 'Введите заголовок' }]}
                        >
                            <Input placeholder="Заголовок уведомления" />
                        </Form.Item>

                        <Form.Item
                            name="message"
                            label="Сообщение"
                            rules={[{ required: true, message: 'Введите сообщение' }]}
                        >
                            <TextArea rows={3} placeholder="Текст уведомления" />
                        </Form.Item>

                        <Form.Item
                            name="category"
                            label="Категория"
                            rules={[{ required: true, message: 'Выберите категорию' }]}
                        >
                            <Select placeholder="Выберите категорию">
                                <Option value="business">Рабочие</Option>
                                <Option value="system">Системные</Option>
                                <Option value="security">Безопасность</Option>
                                <Option value="login">Вход в систему</Option>
                            </Select>
                        </Form.Item>

                        <Form.Item
                            name="payload"
                            label="Дополнительные данные (JSON)"
                        >
                            <TextArea 
                                rows={1} 
                                placeholder='{"url": "/page", "action": "view"}' 
                            />
                        </Form.Item>

                        <Form.Item>
                            <Button 
                                type="primary" 
                                htmlType="submit"
                                size="middle"
                                loading={loading}
                                icon={<SendOutlined />}
                            >
                                Отправить уведомление
                            </Button>
                        </Form.Item>
                    </Form>
                </Card>
            )
        },
        {
            key: 'bulk',
            label: (
                <span><TeamOutlined /> Массовая отправка</span>
            ),
            children: (
                <Card>
                    <Form
                        form={bulkForm}
                        layout="vertical"
                        onFinish={handleSendBulk}
                    >
                        <Form.Item
                            name="user_ids"
                            label="Получатели"
                            rules={[{ required: true, message: 'Выберите получателей' }]}
                        >
                            <Select 
                                mode="multiple" 
                                placeholder="Выберите пользователей"
                                optionLabelProp="label"
                            >
                                {users.map(user => (
                                    <Option 
                                        key={user.id} 
                                        value={user.id}
                                        label={user.name}
                                    >
                                        {user.name} ({user.email})
                                    </Option>
                                ))}
                            </Select>
                        </Form.Item>

                        <Form.Item
                            name="title"
                            label="Заголовок"
                            rules={[{ required: true, message: 'Введите заголовок' }]}
                        >
                            <Input placeholder="Заголовок уведомления" />
                        </Form.Item>

                        <Form.Item
                            name="message"
                            label="Сообщение"
                            rules={[{ required: true, message: 'Введите сообщение' }]}
                        >
                            <TextArea rows={3} placeholder="Текст уведомления" />
                        </Form.Item>

                        <Form.Item
                            name="category"
                            label="Категория"
                            rules={[{ required: true, message: 'Выберите категорию' }]}
                        >
                            <Select placeholder="Выберите категорию">
                                <Option value="business">Рабочие</Option>
                                <Option value="system">Системные</Option>
                                <Option value="security">Безопасность</Option>
                                <Option value="login">Вход в систему</Option>
                            </Select>
                        </Form.Item>

                        <Form.Item
                            name="payload"
                            label="Дополнительные данные (JSON)"
                        >
                            <TextArea 
                                rows={2} 
                                placeholder='{"url": "/page", "action": "view"}' 
                            />
                        </Form.Item>

                        <Form.Item>
                            <Button 
                                type="primary" 
                                htmlType="submit" 
                                loading={loading}
                                icon={<SendOutlined />}
                            >
                                Отправить всем
                            </Button>
                        </Form.Item>
                    </Form>
                </Card>
            )
        },
        {
            key: 'stats',
            label: (
                <span><BarChartOutlined /> Статистика</span>
            ),
            children: (
                <Card>
                    <Row gutter={16}>
                        <Col span={8}>
                            <Statistic
                                title="Всего отправлено"
                                value={stats?.total_sent || 0}
                                prefix={<SendOutlined />}
                            />
                        </Col>
                        <Col span={8}>
                            <Statistic
                                title="Доставлено"
                                value={stats?.total_delivered || 0}
                                prefix={<CheckCircleOutlined />}
                                valueStyle={{ color: '#3f8600' }}
                            />
                        </Col>
                        <Col span={8}>
                            <Statistic
                                title="Не доставлено"
                                value={stats?.total_failed || 0}
                                prefix={<CloseCircleOutlined />}
                                valueStyle={{ color: '#cf1322' }}
                            />
                        </Col>
                    </Row>
                    
                    <Divider />
                    
                    <Row gutter={16}>
                        <Col span={12}>
                            <Statistic
                                title="Процент доставки"
                                value={stats?.delivery_rate || 0}
                                precision={1}
                                suffix="%"
                                valueStyle={{ color: '#3f8600' }}
                            />
                        </Col>
                        <Col span={12}>
                            <Statistic
                                title="Активных подписок"
                                value={stats?.active_subscriptions || 0}
                                prefix={<BellOutlined />}
                            />
                        </Col>
                    </Row>

                    <Divider />

                    <Space>
                        <Button onClick={loadStats} loading={loading}>
                            Обновить статистику
                        </Button>
                        <Button onClick={handleSubscribe} type="dashed">
                            Подписаться на уведомления
                        </Button>
                    </Space>
                </Card>
            )
        }
    ];

    /** Рендер инициализации */
    if (!isInitialized) {
        return (
            <Alert
                
                message={<span className='text-base sm:text-lg !font-medium'>Инициализация системы уведомлений</span>}
                description={<span className='text-sm sm:text-base'>Пожалуйста, подождите...</span>}
                type="info"
                showIcon
            />
        );
    }

    return (
        <>
            <h2><BellOutlined /> Управление Push-уведомлениями </h2>
            <p className='text-base'>Система отправки push-уведомлений для портала</p>

            <div className='mt-2 mb-2'>
                {renderPermissionAlert()}
            </div>

            {user?.role === 'superadmin' && (
                <Tabs items={tabItems} />
            )}
        </>
    );
};

export default NotificationManager;
