# Course Bot — Telegram-бот продажи онлайн-курсов

Telegram-бот на Python для продажи онлайн-курсов с оплатой через ЮKassa.

## Возможности

- Каталог курсов с описанием и ценами
- Корзина — добавление и удаление курсов
- Оплата через ЮKassa (redirect-схема)
- Автоматическая выдача ссылок на материалы после оплаты
- Админ-панель: добавление/удаление курсов, статистика продаж

## Стек

- Python 3.12
- aiogram 3.x
- SQLAlchemy + aiosqlite (SQLite)
- ЮKassa (yookassa SDK)
- aiohttp (webhook-сервер)
- Docker

## Структура проекта

```
course-bot/
├── bot/
│   ├── __init__.py
│   ├── __main__.py          # Точка входа
│   ├── config.py             # Конфигурация из .env
│   ├── handlers/
│   │   ├── __init__.py       # Регистрация роутеров
│   │   ├── start.py          # /start, каталог, мои курсы
│   │   ├── cart.py           # Корзина и оформление заказа
│   │   ├── payment.py        # Webhook ЮKassa
│   │   └── admin.py          # Админ-панель
│   ├── keyboards/
│   │   ├── __init__.py
│   │   └── inline.py         # Инлайн-клавиатуры
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py           # Базовый класс, движок БД
│   │   ├── user.py           # Модель User
│   │   ├── course.py         # Модель Course
│   │   └── order.py          # Модели Order, OrderItem, Payment
│   └── services/
│       ├── __init__.py
│       ├── db.py             # CRUD-операции с БД
│       └── payment.py        # Работа с API ЮKassa
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Быстрый старт

### 1. Клонирование и настройка

```bash
git clone <url-репозитория>
cd course-bot
cp .env.example .env
```

Отредактируй `.env` — заполни все переменные:

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен бота от @BotFather |
| `YOOKASSA_SHOP_ID` | ID магазина в ЮKassa |
| `YOOKASSA_SECRET` | Секретный ключ ЮKassa |
| `ADMIN_IDS` | Telegram ID админов через запятую |
| `WEBHOOK_HOST` | Публичный URL сервера (для webhook ЮKassa) |
| `WEBHOOK_PORT` | Порт webhook-сервера (по умолчанию 8080) |
| `DATABASE_URL` | Строка подключения к БД (по умолчанию SQLite) |

### 2. Запуск через Docker (рекомендуется)

```bash
docker compose up -d --build
```

Бот запустится и будет слушать:
- Telegram polling — для сообщений пользователей
- HTTP порт 8080 — для webhook ЮKassa

### 3. Запуск без Docker

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
python -m bot
```

### 4. Настройка webhook в ЮKassa

В [личном кабинете ЮKassa](https://yookassa.ru/my/) укажи URL для уведомлений:

```
https://yourdomain.com:8080/webhook/yookassa
```

Событие: `payment.succeeded` и `payment.canceled`.

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Приветствие + главное меню |
| `/admin` | Админ-панель (только для ADMIN_IDS) |

## Админ-панель

Доступна только пользователям, чей Telegram ID указан в `ADMIN_IDS`.

Функции:
- **Добавить курс** — пошаговый ввод: название, описание, цена, ссылка на материалы
- **Удалить курс** — выбор из списка активных курсов (мягкое удаление)
- **Статистика** — количество пользователей, заказов, выручка

## База данных

Таблицы:
- `users` — пользователи Telegram
- `courses` — курсы (название, описание, цена, ссылка, активность)
- `orders` — заказы (статус: pending / paid / cancelled)
- `order_items` — элементы заказа (связь заказ ↔ курс)
- `payments` — платежи ЮKassa (статус: pending / succeeded / canceled)

БД создаётся автоматически при первом запуске.

## Лицензия

MIT
