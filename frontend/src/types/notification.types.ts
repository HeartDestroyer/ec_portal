/**
 * Типы для работы с push-уведомлениями
 */

export interface NotificationAction {
    action: string;
    title: string;
    icon?: string;
}

export interface NotificationRequest {
    user_id: string;
    message: string;
    category: 'login' | 'security' | 'system' | 'business';
    title: string;
    payload?: Record<string, any>;
    actions?: NotificationAction[];
}

export interface PushSubscription {
    endpoint: string;
    keys: {
        p256dh: string;
        auth: string;
    };
    user_id: string;
}

export interface Subscription {
    user_id: string;
    subscription_info: PushSubscription;
}

export interface User {
    id: string;
    name: string;
    email: string;
}

export interface NotificationStats {
    total_sent: number;
    total_delivered: number;
    total_failed: number;
    delivery_rate: number;
    active_subscriptions: number;
}