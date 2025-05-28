/** 
 * Сервис для работы с push-уведомлениями
 */

import { apiService } from './api.service';

interface PushSubscription {
  user_id: string;
  subscription_info: any;
}

interface NotificationRequest {
  user_id: string;
  title: string;
  message: string;
  category?: string;
  payload?: any;
  actions?: NotificationAction[];
}

interface NotificationAction {
  action: string;
  title: string;
  icon?: string;
}

interface BulkNotificationRequest {
  user_ids: string[];
  title: string;
  message: string;
  category?: string;
  payload?: any;
  actions?: NotificationAction[];
}

interface NotificationStats {
  total_sent: number;
  total_failed: number;
  total_no_subscription: number;
  active_subscriptions: number;
}

class NotificationService {
  private static instance: NotificationService;
  private swRegistration: ServiceWorkerRegistration | null = null;
  private isSubscribed = false;
  private vapidPublicKey: string | null = null;

  public static getInstance(): NotificationService {
    if (!NotificationService.instance) {
      NotificationService.instance = new NotificationService();
    }
    return NotificationService.instance;
  }

  /**
   * Инициализация службы уведомлений
   */
  async initialize(): Promise<boolean> {
    try {
      if (!('serviceWorker' in navigator)) {
        console.warn('Service Worker не поддерживается');
        return false;
      }

      if (!('PushManager' in window)) {
        console.warn('Push Manager не поддерживается');
        return false;
      }

      // Регистрируем service worker
      this.swRegistration = await navigator.serviceWorker.register('/sw.js');
      console.log('Service Worker зарегистрирован:', this.swRegistration);

      // Проверяем статус подписки
      const subscription = await this.swRegistration.pushManager.getSubscription();
      this.isSubscribed = subscription !== null;

      // Получаем VAPID ключ
      await this.getVapidPublicKey();

      return true;
    } catch (error) {
      console.error('Ошибка инициализации уведомлений:', error);
      return false;
    }
  }

  /**
   * Получение статуса разрешения уведомлений
   */
  getPermissionStatus(): NotificationPermission {
    return Notification.permission;
  }

  /**
   * Запрос разрешения на уведомления
   */
  async requestPermission(): Promise<NotificationPermission> {
    const permission = await Notification.requestPermission();
    return permission;
  }

  /**
   * Получение публичного ключа VAPID
   */
  private async getVapidPublicKey(): Promise<string> {
    if (this.vapidPublicKey) {
      return this.vapidPublicKey;
    }

    try {
      const response = await apiService.get('/notifications/vapid-key') as any;
      this.vapidPublicKey = response.data.data.vapid_public_key;
      if (!this.vapidPublicKey) {
        throw new Error('VAPID ключ не получен');
      }
      return this.vapidPublicKey;
    } catch (error) {
      console.error('Ошибка получения VAPID ключа:', error);
      throw error;
    }
  }

  /**
   * Подписка на push-уведомления
   */
  async subscribe(userId: string): Promise<boolean> {
    try {
      if (!this.swRegistration) {
        throw new Error('Service Worker не зарегистрирован');
      }

      const vapidKey = await this.getVapidPublicKey();

      const subscription = await this.swRegistration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.urlB64ToUint8Array(vapidKey)
      });

      const subscriptionData: PushSubscription = {
        user_id: userId,
        subscription_info: subscription.toJSON()
      };

      await apiService.post('/notifications/subscribe', subscriptionData);

      this.isSubscribed = true;
      return true;
    } catch (error) {
      console.error('Ошибка подписки на уведомления:', error);
      return false;
    }
  }

  /**
   * Отписка от уведомлений
   */
  async unsubscribe(userId: string): Promise<boolean> {
    try {
      if (this.swRegistration) {
        const subscription = await this.swRegistration.pushManager.getSubscription();
        if (subscription) {
          await subscription.unsubscribe();
        }
      }

      await apiService.delete(`/notifications/unsubscribe/${userId}`);

      this.isSubscribed = false;
      return true;
    } catch (error) {
      console.error('Ошибка отписки от уведомлений:', error);
      return false;
    }
  }

  /**
   * Отправка простого уведомления
   */
  async sendNotification(notification: NotificationRequest): Promise<boolean> {
    try {
      await apiService.post('/notifications/send', notification);
      return true;
    } catch (error) {
      console.error('Ошибка отправки уведомления:', error);
      return false;
    }
  }

  /**
   * Проверка статуса подписки
   */
  getSubscriptionStatus(): boolean {
    return this.isSubscribed;
  }

  /**
   * Массовая отправка уведомлений
   */
  async sendBulkNotification(bulkRequest: BulkNotificationRequest): Promise<{sent: number, failed: number, no_subscription: number}> {
    try {
      const response = await apiService.post('/notifications/send-bulk', bulkRequest) as any;
      return response.data.data;
    } catch (error) {
      console.error('Ошибка массовой отправки уведомлений:', error);
      return { sent: 0, failed: 0, no_subscription: 0 };
    }
  }

  /**
   * Получение статистики уведомлений
   */
  async getStats(): Promise<NotificationStats> {
    try {
      const response = await apiService.get('/notifications/stats') as any;
      return response.data.data;
    } catch (error) {
      console.error('Ошибка получения статистики:', error);
      return {
        total_sent: 0,
        total_failed: 0,
        total_no_subscription: 0,
        active_subscriptions: 0
      };
    }
  }

  /**
   * Преобразование VAPID ключа в правильный формат
   */
  private urlB64ToUint8Array(base64String: string): Uint8Array {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }
}

export const notificationService = NotificationService.getInstance();
export default notificationService;
