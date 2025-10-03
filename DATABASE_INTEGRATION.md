# Интеграция с БД Supabase (PostgreSQL)

## 🎯 Что реализовано

Полная интеграция БД для автоматизации работы с Wildberries API:

### ✅ Компоненты

1. **SQL Схема** (`database/schema.sql`)
   - 7 таблиц (products, seller_articles, unit_economics, warehouse_remains, price_history, api_schemas, validation_logs)
   - Индексы (B-tree, GIN для JSONB)
   - Триггеры (автоматическое обновление updated_at)
   - RLS policies (Row Level Security)
   - Views для экспорта
   - Функции (upsert_product_with_variants, update_prices_with_history, cleanup)

2. **Python клиент** (`database/db_client.py`)
   - Централизованное подключение к Supabase
   - Методы для всех CRUD операций
   - Логирование валидации
   - Утилиты обслуживания

3. **Интеграции** (`database/integrations/`)
   - `content_cards_db.py` — синхронизация артикулов из Content API
   - `discounts_prices_db.py` — синхронизация цен из Discounts-Prices API

4. **Главный скрипт** (`database/main_sync.py`)
   - Полная синхронизация (API → БД → Sheets)
   - Режимы: full, articles, prices, export, stats
   - CLI параметры для гибкой настройки

5. **Документация**
   - `database/README.md` — полная документация (анализ, ER-диаграмма, примеры)
   - `database/SETUP.md` — инструкция по настройке
   - `database/queries.sql` — готовые SQL-запросы (80+ примеров)

---

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install supabase
```

### 2. Настройка Supabase

1. Создайте проект на [supabase.com](https://supabase.com)
2. Скопируйте URL и anon key из Settings → API
3. Добавьте в `api_keys.py`:

```python
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-key"
```

### 3. Создание схемы БД

Выполните `database/schema.sql` через SQL Editor в Supabase Dashboard

### 4. Тест подключения

```bash
python database/db_client.py
```

---

## 📊 Использование

### Полная синхронизация

```bash
python database/main_sync.py --mode full
```

### Только артикулы

```bash
python database/main_sync.py --mode articles --max-cards 100
```

### Только цены

```bash
python database/main_sync.py --mode prices --max-goods 50
```

### Статистика

```bash
python database/main_sync.py --mode stats
```

---

## 🗂️ Структура БД

### Основные таблицы

```
Products (товары)
├── nm_id (PK, UNIQUE)
├── vendor_code, brand, title, subject
├── volume (литраж)
└── active

SellerArticles (варианты)
├── id (PK)
├── nm_id (FK → products)
├── barcode (UNIQUE)
└── size

UnitEconomics (цены)
├── nm_id (PK, FK → products)
├── price, discounted_price, discount
├── discount_on_site (СПП)
├── price_after_spp
└── competitive_price

WarehouseRemains (остатки)
├── barcode (FK → seller_articles)
├── warehouse_name
├── quantity
└── snapshot_date
```

### ER-диаграмма

См. `database/README.md` (Mermaid diagram)

---

## 🔗 Интеграция с существующими функциями

### list_of_seller_articles

```python
from database.integrations.content_cards_db import upsert_cards_to_db
from database.db_client import get_client

# После получения cards из API
db_client = get_client()
stats = upsert_cards_to_db(cards, db_client)
```

### discounts_prices

```python
from database.integrations.discounts_prices_db import upsert_prices_to_db
from database.db_client import get_client

# После получения all_goods из API
db_client = get_client()
stats = upsert_prices_to_db(all_goods, db_client)
```

### Экспорт в Google Sheets

```python
from database.db_client import get_client

db_client = get_client()
data = db_client.get_active_articles_for_export()
# Используйте data для записи в Sheets
```

---

## 📝 Примеры SQL-запросов

### Активные артикулы с ценами

```sql
SELECT * FROM v_active_articles_export;
```

### Топ товаров по скидкам

```sql
SELECT p.nm_id, p.brand, ue.discount, ue.price
FROM products p
JOIN unit_economics ue ON p.nm_id = ue.nm_id
ORDER BY ue.discount DESC LIMIT 20;
```

### История изменения цен

```sql
SELECT nm_id, price_after_spp, recorded_at
FROM price_history
WHERE nm_id = 12345678
ORDER BY recorded_at DESC;
```

Больше примеров в `database/queries.sql` (80+ запросов)

---

## 🛠️ Обслуживание

### Очистка старых данных

```python
from database.db_client import get_client

db = get_client()
db.cleanup_old_logs()  # >30 дней
db.cleanup_old_price_history()  # >90 дней
```

### Автоматическая очистка (pg_cron)

```sql
SELECT cron.schedule(
    'cleanup-logs',
    '0 3 * * *',
    'SELECT cleanup_old_logs()'
);
```

---

## 📚 Документация

- **`database/README.md`** — полная документация (анализ, ER-диаграмма, интеграция)
- **`database/SETUP.md`** — инструкция по настройке и troubleshooting
- **`database/queries.sql`** — 80+ готовых SQL-запросов
- **`database/schema.sql`** — полная SQL-схема с комментариями

---

## 🔒 Безопасность

- **RLS (Row Level Security)** — политики для authenticated пользователей
- **JSONB** для гибкого хранения схем и логов
- **Индексы** для производительности
- **Функции** для бизнес-логики (upsert с валидацией)

---

## 📈 Преимущества

1. ✅ **Централизованное хранение** — все данные в одном месте
2. ✅ **История цен** — автоматическое сохранение изменений
3. ✅ **Валидация** — логирование всех операций
4. ✅ **Производительность** — индексы и views
5. ✅ **Масштабируемость** — PostgreSQL + Supabase
6. ✅ **Интеграция** — легко добавить в существующий код

---

**Версия:** 1.0  
**Дата:** 2025-10-03  
**Автор:** AI Assistant

Полная документация: [`database/README.md`](./database/README.md)

