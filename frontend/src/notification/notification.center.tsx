import React, { useEffect, useState } from 'react';
import { Badge, Dropdown, List, Button, Tabs, Spin } from 'antd';
import { BellOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { notification } from 'antd';
import { fetchNotifications, markAllAsRead, markAsRead } from '@/services/notification.service';
import soundUrl from '@/static/audio/notification.mp3';

const NotificationCenter = () => {
    const [visible, setVisible] = useState(false);
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(false);
    const [unread, setUnread] = useState(0);
    const [category, setCategory] = useState('all');

    const audio = new Audio(soundUrl);

    /** Загрузка уведомлений */
    const loadNotifications = async () => {
        setLoading(true);
        const res = await fetchNotifications(category);
        setNotifications(res.data || []);
        setUnread(res.data?.filter((n: any) => !n.is_read).length || 0);
        setLoading(false);
    };
    
    /** Загрузка уведомлений при изменении категории */
    useEffect(() => {
        loadNotifications();
    }, [category]);
    
    /** Отметить все уведомления как прочитанные */
    const handleReadAll = async () => {
        await markAllAsRead();
        loadNotifications();
    };
    
    /** Обработка клика по уведомлению */
    const handleNotificationClick = async (item: any) => {
        if (!item.is_read) await markAsRead(item.id);
        if (item.payload?.url) window.open(item.payload.url, '_blank');
        if (item.type === 'critical') audio.play();
        loadNotifications();
    };
    
    /** Вызов popup через antd notification для срочных */
    useEffect(() => {
        if (notifications.length && notifications[0].type === 'critical' && !notifications[0].is_read) {
            notification.open({
                message: notifications[0].title,
                description: notifications[0].message,
                duration: 0,
                onClick: () => handleNotificationClick(notifications[0]),
                icon: <CheckCircleOutlined style={{ color: '#faad14' }} />,
            });
            audio.play();
        }
    }, [notifications]);
    
    // Фильтры по категориям
    const tabItems = [
        { key: 'all', label: 'Все' },
        { key: 'business', label: 'Бизнес' },
        { key: 'system', label: 'Системные' },
        { key: 'security', label: 'Безопасность' },
        { key: 'login', label: 'Входы' }
    ];
    
    return (
        <Dropdown
            open={visible}
            onOpenChange={setVisible}
            placement="bottomRight"
            overlay={
                <div style={{ width: 340 }}>
                    <Tabs
                        items={tabItems.map(tab => ({
                            key: tab.key,
                            label: tab.label,
                            children: loading ? <Spin /> : (
                                <List
                                    dataSource={notifications.filter(n => category === 'all' || n.category === category)}
                                    renderItem={item => (
                                        <List.Item onClick={() => handleNotificationClick(item)} style={{ cursor: 'pointer', background: item.is_read ? '#fff' : '#f6ffed' }}>
                                        <List.Item.Meta
                                            title={<b>{item.title}</b>}
                                            description={item.message}
                                        />
                                        {!item.is_read && <Badge status="processing" />}
                                        </List.Item>
                                    )}
                                />
                            )
                        }))}
                        onChange={setCategory}
                        activeKey={category}
                    />
                <div style={{ textAlign: 'right', marginTop: 8 }}>
                    <Button size="small" onClick={handleReadAll}>Прочитать всё</Button>
                </div>
                </div>
            }
            trigger={['click']}
        >
            <Badge count={unread} overflowCount={99}>
                <BellOutlined style={{ fontSize: 22, color: '#0D3B66', cursor: 'pointer' }} />
            </Badge>
        </Dropdown>
    );
};
    
export default NotificationCenter;
