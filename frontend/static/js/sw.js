// Service Worker для обработки push-уведомлений
const CACHE_NAME = 'notifications-v1';

// Установка Service Worker
self.addEventListener('install', (event) => {
  console.log('Service Worker установлен');
  self.skipWaiting();
});

// Активация Service Worker
self.addEventListener('activate', (event) => {
  console.log('Service Worker активирован');
  event.waitUntil(self.clients.claim());
});

// Обработка push-уведомлений
self.addEventListener('push', (event) => {
  console.log('Получено push-уведомление:', event);

  let notificationData = {
    title: 'Новое уведомление',
    body: 'У вас есть новое уведомление',
    icon: '/favicon.ico',
    badge: '/favicon.ico',
    tag: 'notification',
    requireInteraction: true,
    actions: [
      {
        action: 'view',
        title: 'Просмотреть',
        icon: '/icons/view.png'
      },
      {
        action: 'dismiss',
        title: 'Закрыть',
        icon: '/icons/close.png'
      }
    ],
    data: {}
  };

  // Парсим данные из push-сообщения
  if (event.data) {
    try {
      const pushData = event.data.json();
      notificationData = {
        ...notificationData,
        title: pushData.title || notificationData.title,
        body: pushData.message || pushData.body || notificationData.body,
        icon: pushData.icon || notificationData.icon,
        badge: pushData.badge || notificationData.badge,
        tag: pushData.category || pushData.tag || notificationData.tag,
        data: pushData.payload || pushData.data || {},
        actions: pushData.actions || notificationData.actions,
        requireInteraction: pushData.requireInteraction !== false
      };
    } catch (error) {
      console.error('Ошибка парсинга push-данных:', error);
    }
  }

  // Показываем уведомление
  const promiseChain = self.registration.showNotification(
    notificationData.title,
    {
      body: notificationData.body,
      icon: notificationData.icon,
      badge: notificationData.badge,
      tag: notificationData.tag,
      data: notificationData.data,
      actions: notificationData.actions,
      requireInteraction: notificationData.requireInteraction,
      silent: false,
      vibrate: [200, 100, 200]
    }
  );

  event.waitUntil(promiseChain);
});

// Обработка кликов по уведомлениям
self.addEventListener('notificationclick', (event) => {
  console.log('Клик по уведомлению:', event);

  const notification = event.notification;
  const action = event.action;
  const data = notification.data || {};

  // Закрываем уведомление
  notification.close();

  if (action === 'dismiss') {
    // Пользователь нажал "Закрыть"
    console.log('Уведомление закрыто пользователем');
    return;
  }

  // Обработка других действий или клика по уведомлению
  const promiseChain = clients.matchAll({
    type: 'window',
    includeUncontrolled: true
  }).then((clientList) => {
    // Ищем открытое окно приложения
    for (let i = 0; i < clientList.length; i++) {
      const client = clientList[i];
      if (client.url.includes(self.location.origin) && 'focus' in client) {
        // Фокусируемся на существующем окне
        return client.focus().then(() => {
          // Отправляем сообщение в приложение
          return client.postMessage({
            type: 'NOTIFICATION_CLICK',
            action: action,
            data: data,
            notification: {
              title: notification.title,
              body: notification.body,
              tag: notification.tag
            }
          });
        });
      }
    }

    // Если окно не найдено, открываем новое
    let urlToOpen = self.location.origin;
    
    // Если есть специальный URL в данных уведомления
    if (data.url) {
      urlToOpen = data.url;
    } else if (action === 'view' && data.viewUrl) {
      urlToOpen = data.viewUrl;
    }

    return clients.openWindow(urlToOpen).then((client) => {
      if (client) {
        return client.postMessage({
          type: 'NOTIFICATION_CLICK',
          action: action,
          data: data,
          notification: {
            title: notification.title,
            body: notification.body,
            tag: notification.tag
          }
        });
      }
    });
  });

  event.waitUntil(promiseChain);
});

// Обработка закрытия уведомлений
self.addEventListener('notificationclose', (event) => {
  console.log('Уведомление закрыто:', event.notification.tag);
  
  // Можно отправить аналитику о закрытии уведомления
  const data = event.notification.data || {};
  if (data.trackClose) {
    // Отправляем информацию о закрытии на сервер
    fetch('/api/v1/notifications/track-close', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        tag: event.notification.tag,
        timestamp: Date.now()
      })
    }).catch(error => {
      console.error('Ошибка отправки аналитики закрытия:', error);
    });
  }
});

// Обработка сообщений от основного потока
self.addEventListener('message', (event) => {
  console.log('Сообщение в Service Worker:', event.data);

  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Обработка ошибок push-уведомлений
self.addEventListener('pushsubscriptionchange', (event) => {
  console.log('Подписка на push изменилась:', event);
  
  // Здесь можно обновить подписку на сервере
  const promiseChain = self.registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: event.oldSubscription?.options?.applicationServerKey
  }).then((newSubscription) => {
    // Отправляем новую подписку на сервер
    return fetch('/api/v1/notifications/update-subscription', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        oldSubscription: event.oldSubscription,
        newSubscription: newSubscription
      })
    });
  }).catch(error => {
    console.error('Ошибка обновления подписки:', error);
  });

  event.waitUntil(promiseChain);
}); 