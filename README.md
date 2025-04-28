# portal
ЭЦ-портал — платформа для управления бизнес-процессами и обучения сотрудников

# ЭЦ-портал Бэкенд

Бэкэнд FastAPI для ЭЦ-портал с расширенными функциями и безопасностью

## Функции
    FastAPI-based REST API
    Async SQLAlchemy с PostgreSQL
    Интеграция с Redis
    JWT аутентификация
    CSRF защита
    Rate limiting - Ограничение скорости / защита от спама
    Управление электронной почтой
    Система логирования
    Тесты

## Требования
    Python 3.11+
    PostgreSQL
    Redis

## Установка
    1. Клонирование репозитория:
    git clone https://github.com/HeartDestroyer/ec_portal.git
    cd ec_portal/backend

    2. Создать и активировать виртуальную среду:
    python -m venv venv
    venv\Scripts\activate

    3. Установите зависимости:
    pip install -r requirements.txt

## Разработка
    1. Запуск:
    uvicorn main:app --reload

## Документация API
    Swagger UI: http://localhost:8000/docs
    ReDoc: http://localhost:8000/redoc


## Логика backend
    Refresh токен всегда хранится в HttpOnly cookie
    Access токен возвращается в теле ответа (и его должен хранить фронт)
    Logout удаляет refresh cookie и отзывает токены
    Обновление токенов использует refresh токен из HttpOnly cookie, возвращает новый access токен и обновляет refresh cookie
    CSRF токен кладётся в обычную cookie (httponly=False), чтобы фронт мог его прочитать