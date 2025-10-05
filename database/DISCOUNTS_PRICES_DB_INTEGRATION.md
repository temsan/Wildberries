# 💰 Discounts-Prices DB Integration

Полная замена Google Sheets интеграции на прямую работу с базой данных.

## 🎯 Что это

Новая система синхронизации цен и скидок из Wildberries API напрямую в PostgreSQL/Supabase, минуя Google Sheets.

## 🏗️ Архитектура

```
WB Discounts-Prices API → DiscountsPricesDBProcessor → PostgreSQL/Supabase
                                     ↓
                            validation_logs (логирование)
                            price_history (история цен)
                            unit_economics (текущие цены)
```

## 📁 Файлы

- `discounts_prices_enhanced.py` - Основной процессор
- `run_discounts_prices_sync.py` - CLI скрипт для запуска
- `discounts_prices_db.py` - Старая версия (для совместимости)

## 🚀 Использование

### 1. Простой запуск
```bash
# Синхронизация всех товаров
python database/run_discounts_prices_sync.py

# Тест подключений
python database/run_discounts_prices_sync.py --test-only

# Ограниченная синхронизация
python database/run_discounts_prices_sync.py --max-goods 500
```

### 2. С параметрами
```bash
# Кастомные параметры
python database/run_discounts_prices_sync.py \
    --max-goods 1000 \
    --batch-size 100 \
    --sleep 2.0 \
    --analytics \
    --export exports/prices.json
```

### 3. Программно
```python
from database.integrations.discounts_prices_enhanced import DiscountsPricesDBProcessor

# Инициализация
processor = DiscountsPricesDBProcessor()

# Проверка подключений
connections = processor.test_connections()

# Синхронизация
stats = processor.sync_prices_to_db(max_goods=1000)

# Аналитика
analytics = processor.get_price_analytics(days=7)

# Экспорт
processor.export_to_json("prices.json", max_goods=500)
```

## 📊 Параметры

### CLI параметры
- `--max-goods` - Максимальное количество товаров
- `--batch-size` - Размер батча (по умолчанию: 50)
- `--sleep` - Задержка между запросами (по умолчанию: 1.0с)
- `--export` - Путь для экспорта в JSON
- `--analytics` - Показать аналитику после синхронизации
- `--test-only` - Только тест подключений

### API параметры
- `page_size` - Размер страницы API (50-1000)
- `sleep_seconds` - Задержка между запросами (1.0+)
- `max_pages` - Лимит страниц

## 🔧 Настройка

### 1. API ключи
Проверьте настройки в `api_keys.py`:
```python
# Discounts-Prices API
AUTHORIZEV3_TOKEN = "your_jwt_token_here"
COOKIES = "wbx-validation-key=...; x-supplier-id-external=..."
USER_AGENT = "Mozilla/5.0..."
```

### 2. База данных
Убедитесь, что БД настроена:
```python
# Supabase
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your_anon_key"
```

## 📈 Аналитика

### Статистика
- Общее количество товаров
- Средняя цена
- Количество товаров со скидками
- Средний размер скидки

### История цен
- Товары с изменениями цен
- Минимальные/максимальные цены
- Динамика изменений

### Пример аналитики
```json
{
  "statistics": {
    "total_products": 1234,
    "avg_price": 2450.50,
    "min_price": 100.00,
    "max_price": 50000.00,
    "products_with_discount": 567,
    "avg_discount": 15.3
  },
  "price_changes": [
    {
      "nm_id": 12345,
      "vendor_code": "VC001",
      "changes_count": 5,
      "min_price": 1200.00,
      "max_price": 1500.00,
      "price_difference": 300.00
    }
  ]
}
```

## 🔄 Процесс синхронизации

### 1. Подключения
- Проверка БД (PostgreSQL/Supabase)
- Проверка API (Discounts-Prices)

### 2. Получение данных
- Итерация по страницам API
- Пагинация с задержками
- Обработка ошибок (401, 429)

### 3. Обработка данных
- Валидация nmID
- Обработка цен (множественные значения)
- Расчет цены после СПП
- Определение промо-акций

### 4. Сохранение в БД
- Upsert в `unit_economics`
- Сохранение истории в `price_history`
- Логирование в `validation_logs`

### 5. Результаты
- Статистика обработки
- Список ошибок
- Время выполнения

## 📋 Логирование

Все операции логируются в таблицу `validation_logs`:

```sql
SELECT * FROM validation_logs 
WHERE operation_type = 'sync_discounts_prices' 
ORDER BY timestamp DESC;
```

### Поля лога
- `operation_type` - Тип операции
- `status` - Статус (success/warning/error)
- `records_processed` - Обработано записей
- `records_failed` - Ошибок
- `input_data` - Пример данных
- `validation_errors` - Детали ошибок
- `execution_time_ms` - Время выполнения

## 🚨 Обработка ошибок

### API ошибки
- **401 Unauthorized** - Неверный токен
- **429 Too Many Requests** - Превышен лимит
- **Timeout** - Превышен таймаут

### БД ошибки
- **Connection** - Проблемы подключения
- **Constraint** - Нарушение ограничений
- **Data** - Ошибки данных

### Стратегии
- Автоматические повторы
- Увеличение задержек
- Пропуск проблемных записей
- Детальное логирование

## 🔍 Мониторинг

### Проверка статуса
```bash
# Тест подключений
python database/run_discounts_prices_sync.py --test-only

# Проверка логов
python -c "
from database.db_client import get_client
client = get_client()
logs = client.client.table('validation_logs').select('*').eq('operation_type', 'sync_discounts_prices').order('timestamp', desc=True).limit(5).execute()
print(logs.data)
"
```

### Метрики производительности
- Время выполнения
- Количество запросов к API
- Скорость обработки (товаров/сек)
- Процент успешных операций

## 🔄 Интеграция с веб-интерфейсом

Новая система интегрируется с веб-интерфейсом:

1. **Вкладка "Синхронизация"** - запуск синхронизации
2. **Вкладка "Цены"** - просмотр результатов
3. **Вкладка "История цен"** - аналитика изменений
4. **Вкладка "Логи"** - мониторинг операций

## 🆚 Сравнение с Google Sheets

| Параметр | Google Sheets | БД Integration |
|----------|---------------|----------------|
| Скорость | Медленно | Быстро |
| Надежность | Зависит от API | Высокая |
| История | Ограниченная | Полная |
| Аналитика | Базовая | Продвинутая |
| Автоматизация | Сложная | Простая |
| Мониторинг | Ограниченный | Полный |

## 🎉 Преимущества

1. **Производительность** - Прямая работа с БД
2. **Надежность** - Транзакции и откаты
3. **История** - Полная история изменений цен
4. **Аналитика** - SQL запросы и отчеты
5. **Автоматизация** - Cron задачи и API
6. **Мониторинг** - Детальные логи и метрики

## 🔮 Планы развития

1. **Автоматическая синхронизация** - Cron задачи
2. **Уведомления** - Email/Telegram при ошибках
3. **Дашборды** - Графики и метрики в реальном времени
4. **API** - REST API для внешних систем
5. **Машинное обучение** - Предсказание цен
