class PushNotificationClient {
    constructor() {
        this.swRegistration = null;
        this.isSubscribed = false;
    }

    async init() {
        try {
            // Проверяем поддержку Service Worker и Push API
            if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
                console.error('Push-уведомления не поддерживаются');
                return false;
            }

            // Регистрируем Service Worker
            this.swRegistration = await navigator.serviceWorker.register('/service-worker.js');
            console.log('Service Worker зарегистрирован');

            // Проверяем текущую подписку
            const subscription = await this.swRegistration.pushManager.getSubscription();
            this.isSubscribed = subscription !== null;

            return true;
        } catch (error) {
            console.error('Ошибка при инициализации push-уведомлений:', error);
            return false;
        }
    }

    async subscribeUser(userId) {
        try {
            // Получаем VAPID публичный ключ с сервера
            const response = await fetch('/api/v1/notifications/vapid-key');
            const data = await response.json();
            const vapidPublicKey = data.data.vapid_public_key;

            // Конвертируем VAPID ключ в Uint8Array
            const applicationServerKey = this.urlB64ToUint8Array(vapidPublicKey);

            // Создаем подписку
            const subscription = await this.swRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: applicationServerKey
            });

            // Отправляем подписку на сервер
            await fetch('/api/v1/notifications/subscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userId,
                    subscription_info: subscription
                })
            });

            this.isSubscribed = true;
            console.log('Пользователь подписан на push-уведомления');
            return true;
        } catch (error) {
            console.error('Не удалось подписать пользователя:', error);
            return false;
        }
    }

    async unsubscribeUser(userId) {
        try {
            const subscription = await this.swRegistration.pushManager.getSubscription();
            if (subscription) {
                // Отменяем подписку
                await subscription.unsubscribe();
                
                // Удаляем подписку на сервере
                await fetch(`/api/v1/notifications/unsubscribe/${userId}`, {
                    method: 'DELETE'
                });

                this.isSubscribed = false;
                console.log('Пользователь отписан от push-уведомлений');
                return true;
            }
            return false;
        } catch (error) {
            console.error('Ошибка при отписке от push-уведомлений:', error);
            return false;
        }
    }

    // Вспомогательная функция для конвертации base64 в Uint8Array
    urlB64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }
}
