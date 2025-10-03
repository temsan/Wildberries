# Инструкция по настройке БД Supabase

## 📋 Быстрый старт

### Шаг 1: Создание проекта в Supabase

1. Перейдите на [supabase.com](https://supabase.com)
2. Создайте аккаунт (или войдите)
3. Нажмите "New Project"
4. Заполните:
   - **Name**: `wildberries-api` (или любое другое)
   - **Database Password**: сгенерируйте надежный пароль
   - **Region**: выберите ближайший (например, Frankfurt для РФ)
5. Дождитесь создания проекта (~2 минуты)

### Шаг 2: Получение credentials

После создания проекта:

1. Перейдите в **Settings** → **API**
2. Скопируйте:
   - **Project URL** (например, `https://abcdefgh.supabase.co`)
   - **anon public key** (длинный JWT токен)

### Шаг 3: Добавление credentials в проект

Откройте `api_keys.py` и добавьте в конец файла:

```python
# ============================================================================
# SUPABASE DATABASE
# ============================================================================
SUPABASE_URL = "https://your-project.supabase.co"  # Замените на свой URL
SUPABASE_KEY = "your-anon-key-here"  # Замените на свой anon key
```

### Шаг 4: Установка зависимостей

```bash
pip install supabase
```

Или обновите все зависимости:

```bash
pip install -r requirements.txt
```

### Шаг 5: Создание схемы БД

1. В Supabase Dashboard перейдите в **SQL Editor**
2. Создайте новый запрос (New query)
3. Скопируйте содержимое файла [`schema.sql`](./schema.sql)
4. Вставьте в редактор
5. Нажмите **Run** (или Ctrl+Enter)
6. Дождитесь завершения (~10-20 секунд)

**Проверка:**
- Перейдите в **Table Editor**
- Должны появиться таблицы: `products`, `seller_articles`, `unit_economics`, и др.

### Шаг 6: Тест подключения

Запустите тестовый скрипт:

```bash
python database/db_client.py
```

Ожидаемый результат:
```
✅ Подключение к Supabase успешно
✅ Supabase готов к работе
📦 Активных товаров: 0
📝 Последних логов: 0
```

---

## 🚀 Использование

### Базовая синхронизация

#### 1. Полная синхронизация (всё сразу)

```bash
python database/main_sync.py --mode full
```

Выполняет:
- Загрузка артикулов из Content Cards API → БД
- Загрузка цен из Discounts-Prices API → БД
- Подготовка данных для экспорта в Google Sheets
- Вывод статистики

#### 2. Только артикулы

```bash
python database/main_sync.py --mode articles
```

#### 3. Только цены

```bash
python database/main_sync.py --mode prices
```

#### 4. Только статистика

```bash
python database/main_sync.py --mode stats
```

### Параметры

- `--max-cards N` — лимит карточек для обработки (для теста)
- `--max-goods N` — лимит товаров для обработки (для теста)

**Примеры:**

```bash
# Тест на 100 карточках
python database/main_sync.py --mode articles --max-cards 100

# Тест на 50 товарах
python database/main_sync.py --mode prices --max-goods 50

# Полная синхронизация с лимитами
python database/main_sync.py --mode full --max-cards 500 --max-goods 500
```

---

## 🔧 Интеграция с существующими функциями

### Пример 1: Использование в list_of_seller_articles

Добавьте в `main_function/list_of_seller_articles_mf/list_of_seller_articles.py`:

```python
# В начало файла
from database.integrations.content_cards_db import sync_content_cards_to_db
from database.db_client import get_client

# В функцию main()
def main():
    # ... существующий код получения карточек ...
    
    # Добавляем сохранение в БД
    db_client = get_client()
    if db_client.test_connection():
        print("💾 Сохраняем артикулы в БД...")
        from database.integrations.content_cards_db import upsert_cards_to_db
        stats = upsert_cards_to_db(cards, db_client)
        print(f"✅ Сохранено: {stats['success']} товаров, {stats['total_variants']} баркодов")
    
    # ... существующий код записи в Google Sheets ...
```

### Пример 2: Использование в discounts_prices

Добавьте в `main_function/discounts_prices_mf/discounts_prices.py`:

```python
# В начало файла
from database.integrations.discounts_prices_db import upsert_prices_to_db
from database.db_client import get_client

# В функцию main()
def main():
    # ... существующий код получения цен ...
    
    # Добавляем сохранение в БД
    db_client = get_client()
    if db_client.test_connection():
        print("💾 Сохраняем цены в БД...")
        stats = upsert_prices_to_db(all_goods, db_client)
        print(f"✅ Сохранено: {stats['success']} цен")
    
    # ... существующий код записи в Google Sheets ...
```

### Пример 3: Экспорт из БД в Google Sheets

Создайте новый файл `excel_actions/utils/export_from_db.py`:

```python
from database.db_client import get_client

def export_active_articles_from_db_to_sheets(spreadsheet_id: str, sheet_name: str):
    """
    Экспорт активных артикулов из БД в Google Sheets.
    """
    db_client = get_client()
    
    # Получаем данные из view
    data = db_client.get_active_articles_for_export()
    
    # Конвертируем в формат для Sheets
    rows = []
    for item in data:
        rows.append([
            item['nm_id'],
            item['vendor_code'],
            item['barcode'],
            item['size'],
            item['brand'],
            item['title'],
            item['volume'],
            item['price'],
            item['discounted_price'],
            item['discount'],
            item['discount_on_site'],
            item['price_after_spp'],
            item['competitive_price']
        ])
    
    # Используйте существующий google_sheets_writer для записи
    # ...
    
    return len(rows)
```

---

## 📊 SQL-запросы для аналитики

### Получить товары с максимальными скидками

```sql
SELECT 
    p.nm_id,
    p.vendor_code,
    p.brand,
    ue.discount,
    ue.price,
    ue.discounted_price
FROM products p
JOIN unit_economics ue ON p.nm_id = ue.nm_id
WHERE p.active = true
ORDER BY ue.discount DESC
LIMIT 20;
```

### Статистика по брендам

```sql
SELECT 
    p.brand,
    COUNT(DISTINCT p.nm_id) AS товаров,
    COUNT(DISTINCT sa.barcode) AS баркодов,
    AVG(ue.price) AS средняя_цена
FROM products p
LEFT JOIN seller_articles sa ON p.nm_id = sa.nm_id
LEFT JOIN unit_economics ue ON p.nm_id = ue.nm_id
WHERE p.active = true
GROUP BY p.brand
ORDER BY товаров DESC;
```

### История изменения цен

```sql
SELECT 
    ph.nm_id,
    p.vendor_code,
    ph.price_after_spp,
    ph.recorded_at
FROM price_history ph
JOIN products p ON ph.nm_id = p.nm_id
WHERE ph.nm_id = 12345678  -- замените на нужный nmID
ORDER BY ph.recorded_at DESC;
```

Запустить SQL в Supabase:
1. Dashboard → SQL Editor
2. Вставить запрос
3. Run

Или через Python:

```python
from database.db_client import get_client

db = get_client()
result = db.client.table('products').select('*').eq('brand', 'MyBrand').execute()
print(result.data)
```

---

## 🛠️ Обслуживание

### Очистка старых данных

#### Автоматическая (рекомендуется)

Настройте в Supabase Dashboard → Database → Extensions → pg_cron:

```sql
-- Включить pg_cron
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Ежедневная очистка логов в 3:00 UTC
SELECT cron.schedule(
    'cleanup-logs',
    '0 3 * * *',
    'SELECT cleanup_old_logs()'
);

-- Еженедельная очистка истории цен (воскресенье в 4:00 UTC)
SELECT cron.schedule(
    'cleanup-price-history',
    '0 4 * * 0',
    'SELECT cleanup_old_price_history()'
);
```

#### Ручная очистка

Через Python:

```python
from database.db_client import get_client

db = get_client()

# Очистить старые логи (>30 дней)
deleted_logs = db.cleanup_old_logs()
print(f"Удалено логов: {deleted_logs}")

# Очистить старую историю цен (>90 дней)
deleted_history = db.cleanup_old_price_history()
print(f"Удалено записей истории: {deleted_history}")
```

Или через SQL Editor в Supabase:

```sql
SELECT cleanup_old_logs();
SELECT cleanup_old_price_history();
```

### Мониторинг

Проверка состояния БД:

```bash
python database/main_sync.py --mode stats
```

Или через SQL:

```sql
-- Статистика по таблицам
SELECT 
    'products' AS table_name,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE active = true) AS active
FROM products
UNION ALL
SELECT 'seller_articles', COUNT(*), COUNT(*) FILTER (WHERE active = true)
FROM seller_articles
UNION ALL
SELECT 'unit_economics', COUNT(*), COUNT(*) FILTER (WHERE price IS NOT NULL)
FROM unit_economics;
```

---

## ⚠️ Troubleshooting

### Ошибка: "Supabase credentials not found"

**Решение:** Добавьте `SUPABASE_URL` и `SUPABASE_KEY` в `api_keys.py`

### Ошибка: "supabase module not found"

**Решение:**
```bash
pip install supabase
```

### Ошибка: "relation products does not exist"

**Решение:** Выполните `schema.sql` через SQL Editor в Supabase Dashboard

### Медленные запросы

**Решение:** Проверьте индексы в Table Editor → выберите таблицу → Indexes

Добавьте индекс вручную через SQL Editor:

```sql
CREATE INDEX idx_custom ON table_name(column_name);
```

### Превышен лимит БД (free tier)

Free tier Supabase:
- 500 MB хранилища
- 2 GB bandwidth/месяц

**Решение:**
1. Регулярно очищайте старые данные
2. Используйте `LIMIT` в запросах
3. Рассмотрите upgrade на Pro план ($25/месяц)

---

## 🔒 Безопасность

### RLS (Row Level Security)

По умолчанию все таблицы защищены RLS с политикой для `authenticated` пользователей.

Для более детальной настройки:

```sql
-- Пример: только чтение для анонимных пользователей
CREATE POLICY products_read_anon ON products
    FOR SELECT
    TO anon
    USING (active = true);

-- Пример: только свои данные для каждого пользователя
CREATE POLICY products_user_policy ON products
    FOR ALL
    TO authenticated
    USING (user_id = auth.uid());
```

### API Keys

- **anon key** — безопасен для клиентской стороны (с RLS)
- **service_role key** — НЕ безопасен, используйте только на сервере

В `api_keys.py` используйте **anon key**.

---

## 📚 Дополнительные ресурсы

- [Supabase Documentation](https://supabase.com/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Supabase Python Client](https://github.com/supabase-community/supabase-py)

---

**Версия:** 1.0  
**Дата:** 2025-10-03

