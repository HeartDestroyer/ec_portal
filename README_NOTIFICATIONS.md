# 🔔 Система Push-уведомлений для корпоративного портала

Полнофункциональная система push-уведомлений с поддержкой браузерных уведомлений, массовой отправки и статистики доставки.

## 🚀 Основные возможности

- **Browser Push Notifications** - Уведомления работают даже при закрытой вкладке
- **Массовая отправка** - Отправка уведомлений группам пользователей
- **Статистика доставки** - Отслеживание успешности доставки
- **Категоризация** - Разделение уведомлений по типам (рабочие, системные, безопасность)
- **Веб-интерфейс** - Удобное управление через браузер

## 📋 Готовые сценарии использования

Система поддерживает отправку уведомлений для различных бизнес-процессов:

- **Завершение обучения** - Уведомление руководителя о прохождении курса сотрудником
- **Заявки на отпуск** - Уведомление о новых заявках на отпуск
- **Подпись документов** - Напоминания о необходимости подписать документы
- **Напоминания о встречах** - Уведомления за 15 минут до начала встречи
- **Назначение задач** - Уведомления о новых задачах
- **Дедлайны** - Напоминания о приближающихся сроках

## ⚡ Быстрый старт

### Backend (Python/FastAPI)

```bash
# Установка зависимостей
pip install fastapi uvicorn pywebpush redis

# Генерация VAPID ключей
python -c "
from pywebpush import webpush
vapid_keys = webpush.generate_vapid_keys()
print('VAPID_PRIVATE_KEY=' + vapid_keys['private_key'])
print('VAPID_PUBLIC_KEY=' + vapid_keys['public_key'])
"

# Добавить ключи в .env файл
echo "VAPID_PRIVATE_KEY=your_private_key" >> .env
echo "VAPID_PUBLIC_KEY=your_public_key" >> .env
echo "VAPID_CLAIM_EMAIL=your-email@company.com" >> .env

# Запуск системы
uvicorn main:app --reload
```

### Frontend (React/TypeScript)

```bash
# Установка зависимостей
npm install antd @ant-design/icons

# Запуск
npm start
```

## 💻 Использование в коде

### Отправка простого уведомления

```python
from backend.api.v1.notifications.utils import NotificationHelper

# Уведомление о завершении обучения
await NotificationHelper.send_simple(
    db=db, redis=redis,
    user_id=123,
    title="Обучение завершено",
    message="Сотрудник Иван Петров завершил курс 'Основы Python'",
    category="business"
)
```

### Массовая отправка

```python
# Уведомление всем сотрудникам отдела
await NotificationHelper.send_bulk(
    db=db, redis=redis,
    user_ids=[123, 456, 789],
    title="Важное объявление",
    message="Завтра в 14:00 общее собрание",
    category="business"
)
```

## 🌐 API Endpoints

### Подписка на уведомления
```http
POST /api/v1/notifications/subscribe
Content-Type: application/json

{
    "user_id": 123,
    "subscription_info": {
        "endpoint": "https://fcm.googleapis.com/...",
        "keys": {
            "p256dh": "...",
            "auth": "..."
        }
    }
}
```

### Отправка уведомления
```http
POST /api/v1/notifications/send
Content-Type: application/json

{
    "user_id": 123,
    "title": "Заголовок",
    "message": "Текст уведомления",
    "category": "business",
    "payload": {"url": "/page"}
}
```

### Массовая отправка
```http
POST /api/v1/notifications/send-bulk
Content-Type: application/json

{
    "user_ids": [123, 456, 789],
    "title": "Заголовок",
    "message": "Текст уведомления",
    "category": "business"
}
```

### Статистика
```http
GET /api/v1/notifications/stats

Response:
{
    "total_sent": 1250,
    "total_delivered": 1180,
    "total_failed": 70,
    "delivery_rate": 94.4,
    "active_subscriptions": 45
}
```

## 📁 Структура проекта

```
backend/
├── api/v1/notifications/
│   ├── models.py          # Модели данных
│   ├── routes.py          # API маршруты
│   ├── service.py         # Бизнес-логика
│   ├── schemas.py         # Схемы запросов/ответов
│   └── utils.py           # Вспомогательные функции
└── examples/
    └── notification_examples.py  # Примеры использования

frontend/
├── src/
│   ├── services/
│   │   └── notification.service.ts  # API клиент
│   ├── components/
│   │   └── NotificationManager.tsx  # Компонент управления
│   └── types/
│       └── notification.types.ts    # TypeScript типы
└── public/
    └── service-worker.js            # Service Worker
```

## 🎛️ Интерфейс управления

Веб-интерфейс включает три основные вкладки:

### 1. Одиночное уведомление
- Выбор получателя из списка
- Ввод заголовка и сообщения
- Выбор категории уведомления
- Дополнительные данные в формате JSON

### 2. Массовая отправка
- Выбор нескольких получателей
- Общий заголовок и сообщение
- Статистика отправки в реальном времени

### 3. Статистика
- Общее количество отправленных уведомлений
- Количество доставленных и неудачных
- Процент успешной доставки
- Количество активных подписок

## 🔐 Безопасность

- **VAPID ключи** - Безопасная аутентификация с push-сервисами
- **Подписки пользователей** - Контроль доступа к уведомлениям
- **Валидация данных** - Проверка всех входящих запросов

## 📊 Мониторинг и статистика

Система отслеживает:
- Общее количество отправленных уведомлений
- Процент успешной доставки
- Количество активных подписок
- Логирование всех операций

## 🔧 Service Worker

Создайте файл `public/service-worker.js`:

```javascript
self.addEventListener('push', function(event) {
    if (event.data) {
        const data = event.data.json();
        const options = {
            body: data.message,
            icon: '/icon-192x192.png',
            badge: '/badge-72x72.png',
            data: data.payload
        };
        
        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    
    if (event.notification.data && event.notification.data.url) {
        event.waitUntil(
            clients.openWindow(event.notification.data.url)
        );
    }
});
```

## 🔗 Интеграция с бизнес-процессами

### Завершение обучения
```python
# В системе обучения после завершения курса
await NotificationHelper.send_simple(
    db=db, redis=redis,
    user_id=manager_id,
    title="Обучение завершено",
    message=f"Сотрудник {employee_name} завершил курс '{course_name}'",
    category="business",
    payload={"url": "/training/certificates", "employee_id": employee_id}
)
```

### Заявка на отпуск
```python
# При подаче заявки на отпуск
await NotificationHelper.send_simple(
    db=db, redis=redis,
    user_id=manager_id,
    title="Новая заявка на отпуск",
    message=f"{employee_name} подал заявку на отпуск с {start_date} по {end_date}",
    category="business",
    payload={"url": "/hr/vacation-requests", "request_id": request_id}
)
```

## 🐛 Устранение неполадок

### Уведомления не приходят
1. Проверьте разрешения браузера на уведомления
2. Убедитесь, что Service Worker зарегистрирован
3. Проверьте VAPID ключи в настройках

### Ошибки подписки
1. Проверьте HTTPS соединение (обязательно для push-уведомлений)
2. Убедитесь, что Redis доступен
3. Проверьте логи сервера

### Низкий процент доставки
1. Проверьте активность пользователей
2. Убедитесь, что подписки не истекли
3. Проверьте настройки браузера пользователей

## 📞 Поддержка

Для получения помощи:
- Проверьте логи в консоли браузера
- Изучите логи сервера
- Убедитесь в правильности настройки VAPID ключей

## 🚀 Планы развития

- Поддержка мобильных приложений
- Расширенная аналитика
- A/B тестирование уведомлений
- Интеграция с внешними системами 