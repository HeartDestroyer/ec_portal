# ЭЦ Портал Backend
## ЭЦ Портал — серверная часть приложения для управления пользователями, сессиями, аутентификацией (JWT + Redis), защитой CSRF и отправкой email-уведомлений.

### Основные функции:
- Аутентификация пользователей
- Управление сессиями (создание, деактивация, фильтрация)
- Хранение и отзыв JWT-токенов в Redis
- Защита CSRF для state-changing запросов
- Отправка писем для верификации email и сброса пароля
- Ограничитель скорости запросов

### Структура проекта
├── api/v1
│   ├── auth      # Роуты и логика аутентификации
│   ├── session   # Роуты и сервис для управления сессиями
│   ├── user      # CRUD пользователей
│   ├── cache     # Возможность очистки кэша FastAPICache
│   └── telegram  # Интеграция с Telegram
├── core
│   ├── config   # Конфигурация через Pydantic BaseSettings
│   ├── extensions
│   │   ├── database.py  # Инициализация SQLAlchemy Async engine
│   │   ├── redis.py     # RedisClient wrapper
│   │   └── logger.py    # Логгер приложения
│   ├── models    # SQLAlchemy-модели (User, Session и др.)
│   └── security  # JWTHandler, CSRFProtection и PasswordManager
└── main.py       # Точка входа, настройка FastAPI, CORS, middleware и lifecycle