self.addEventListener('push', function(event) {
    if (event.data) {
        const data = event.data.json();
        const options = {
            body: data.message,
            icon: data.icon || '/static/notification-icon.png',
            badge: data.badge || '/static/badge-icon.png',
            image: data.image,
            data: data.data,
            actions: data.actions || [
                { action: 'confirm', title: 'Подтвердить' },
                { action: 'reject', title: 'Отклонить' },
                { action: 'details', title: 'Подробнее' }
            ],
            requireInteraction: true,
            vibrate: [200, 100, 200]
        };

        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();

    // Обработка действий уведомления
    if (event.action === 'confirm') {
        // Логика для подтверждения
        handleNotificationAction('confirm', event.notification.data);
    } else if (event.action === 'reject') {
        // Логика для отклонения
        handleNotificationAction('reject', event.notification.data);
    } else if (event.action === 'details') {
        // Открытие страницы с деталями
        if (event.notification.data && event.notification.data.payload && event.notification.data.payload.url) {
            event.waitUntil(
                clients.openWindow(event.notification.data.payload.url)
            );
        }
    }
});

async function handleNotificationAction(action, data) {
    try {
        // Отправляем информацию о действии на сервер
        const response = await fetch('/api/v1/notifications/action', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: action,
                category: data.category,
                payload: data.payload
            })
        });

        if (!response.ok) {
            throw new Error('Не удалось обработать действие уведомления');
        }

        const result = await response.json();
        console.log('Действие уведомления обработано:', result);

        // Если есть URL для перенаправления, открываем его
        if (result.data && result.data.redirect_url) {
            await clients.openWindow(result.data.redirect_url);
        }
    } catch (error) {
        console.error('Ошибка при обработке действий уведомления:', error);
    }
} 