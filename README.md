# 🚀 Wildberries API Dashboard

Комплексное решение для автоматизации работы с Wildberries API с веб-интерфейсом и базой данных.

## 📋 Что это

Проект для полной автоматизации работы с Wildberries:
- **wb_api/**: клиенты API (Content, Warehouse, Discounts-Prices)
- **excel_actions/**: интеграция с Google Sheets (чтение/запись/валидация)
- **database/**: веб-интерфейс и база данных Supabase

## 🚀 Быстрый старт

### 1. Установка
```bash
# Активировать виртуальное окружение (Windows)
.venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt
```

### 2. Настройка API ключей
Отредактируйте `api_keys.py` с вашими ключами:
- WB API ключи
- Google Sheets credentials
- Supabase настройки

### 3. Запуск

#### Веб-интерфейс (новый эргономичный дизайн):
```bash
python database/web_interface.py
# Открыть: http://localhost:8501
# Вкладки сверху, темная тема, компактный дизайн
```

#### Миграции БД:
```bash
python database/run_migration.py
# При проблемах с сетью - см. database/МИГРАЦИЯ_РУЧНАЯ.md
```

## 📁 Структура проекта

```
📦 Wildberries API Dashboard
├── api_keys.py                    # API ключи и настройки
├── requirements.txt               # Зависимости Python
├── README.md                     # Документация

├── wb_api/                       # Клиенты Wildberries API
│   ├── content_cards.py          # Карточки товаров
│   ├── warehouse_remains.py      # Остатки на складах
│   └── discounts_prices/         # Цены и скидки
│       ├── discounts_prices.py
│       └── response_*.json

├── excel_actions/                # Интеграция с Google Sheets
│   ├── list_of_seller_articles_ea/   # Артикулы продавца
│   ├── discounts_prices_ea/           # Цены и скидки
│   ├── warehouse_remains_ea/         # Остатки склада
│   └── utils/                        # Утилиты
│       ├── header_mapping.py
│       ├── schemas/*.json
│       └── sheets_last_updated.py

└── database/                     # Веб-интерфейс и БД
    ├── web_interface.py          # Streamlit интерфейс
    ├── run_migration.py          # Миграции БД
    ├── schema.sql               # Схема БД
    ├── queries.sql              # Готовые запросы
    ├── db_client.py             # Клиент Supabase
    ├── main_sync.py             # Синхронизация данных
    └── migrations/              # Миграции БД
        └── 001_fix_security_issues.sql
```

## 🔧 Функции

### 🌐 Wildberries API
- **Content API**: загрузка карточек товаров
- **Warehouse API**: остатки на складах
- **Discounts-Prices API**: цены и скидки

### 📊 Google Sheets
- Автоматическая загрузка данных
- Валидация структур данных
- Обновление существующих листов

### 🗄️ База данных (Supabase)
- PostgreSQL с RLS политиками
- Автоматическая синхронизация
- Веб-интерфейс для управления

### 🎨 Веб-интерфейс
- Темная тема с бирюзовыми акцентами
- Компактная разметка без прокруток
- Дашборды и аналитика

## 🔐 Конфигурация

Все настройки в `api_keys.py`:
- **WB API ключи** (получить в личном кабинете WB)
- **Google Sheets** (сервис-аккаунт в Google Cloud)
- **Supabase** (проект в supabase.com)

## 🚀 Расширения

Проект готов к расширению:
- Добавление новых WB API (статистика, отзывы)
- Интеграция с другими платформами
- Расширение аналитики и отчетов
