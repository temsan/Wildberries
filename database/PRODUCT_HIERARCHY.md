# 📦 Иерархия продуктов WB API

## 🏗️ Структура данных

```
PRODUCT (nmID) 
    ↓ 1:N
VENDOR_CODE (артикул продавца)
    ↓ 1:N  
BARCODES = SIZES (штрихкоды = размеры)
```

**Бизнес-логика:**
- **Баркод = Размер товара** (кофта M, L, XL)
- **Управление = По артикулу** (весь товар целиком)
- **Цены = Общие для всех размеров**
- **Закупки = По артикулу** (каких-то больше, каких-то меньше)

## 📊 Детальная схема

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTS (nmID)                         │
├─────────────────────────────────────────────────────────────┤
│ • nm_id (INTEGER) - Артикул WB (уникальный)               │
│ • vendor_code (VARCHAR) - Артикул продавца                │
│ • brand (VARCHAR) - Бренд                                  │
│ • title (TEXT) - Название товара                          │
│ • subject (VARCHAR) - Категория/класс                     │
│ • volume (DECIMAL) - Объем упаковки (л)                   │
│ • active (BOOLEAN) - Активность товара                    │
└─────────────────────────────────────────────────────────────┘
                                │
                                │ 1:N (один продукт → много баркодов)
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                SELLER_ARTICLES (barcodes)                  │
├─────────────────────────────────────────────────────────────┤
│ • nm_id (INTEGER) - Ссылка на products.nm_id              │
│ • vendor_code (VARCHAR) - Дублирование для быстрого доступа│
│ • barcode (VARCHAR) - Штрихкод (уникальный)               │
│ • size (VARCHAR) - Размер товара                          │
│ • active (BOOLEAN) - Активность варианта                  │
└─────────────────────────────────────────────────────────────┘
                                │
                                │ 1:1 (один баркод → одна цена)
                                ▼
┌─────────────────────────────────────────────────────────────┐
│              UNIT_ECONOMICS (цены и скидки)               │
├─────────────────────────────────────────────────────────────┤
│ • nm_id (INTEGER) - Ссылка на products.nm_id              │
│ • vendor_code (VARCHAR) - Дублирование для быстрого доступа│
│ • price (DECIMAL) - Цена продавца                         │
│ • discounted_price (DECIMAL) - Цена розничная             │
│ • discount (INTEGER) - Скидка продавца (%)                │
│ • discount_on_site (INTEGER) - СПП (%)                    │
│ • price_after_spp (DECIMAL) - Цена после СПП              │
│ • competitive_price (DECIMAL) - Привлекательная цена      │
│ • is_competitive_price (BOOLEAN) - Статус привлекательной │
│ • has_promotions (BOOLEAN) - Наличие промо                │
└─────────────────────────────────────────────────────────────┘
```

## 🔗 Связи между таблицами

### 1. PRODUCTS → SELLER_ARTICLES
- **Связь**: 1:N (один продукт может иметь несколько баркодов)
- **Ключ**: `products.nm_id` → `seller_articles.nm_id`
- **Пример**: 
  - Продукт nmID=12345 (Футболка Nike)
  - Может иметь баркоды: 1234567890123 (размер M), 1234567890124 (размер L)

### 2. PRODUCTS → UNIT_ECONOMICS  
- **Связь**: 1:1 (один продукт имеет одну цену)
- **Ключ**: `products.nm_id` → `unit_economics.nm_id`
- **Пример**:
  - Продукт nmID=12345
  - Цена: 1500₽, со скидкой: 1350₽, СПП: 10%

### 3. SELLER_ARTICLES → UNIT_ECONOMICS
- **Связь**: N:1 (несколько баркодов → одна цена на продукт)
- **Ключ**: `seller_articles.nm_id` → `unit_economics.nm_id`
- **Логика**: Цены привязаны к продукту, а не к конкретному баркоду

## 📈 Примеры данных

### Продукт с множественными баркодами
```sql
-- Продукт
INSERT INTO products VALUES (
    12345,           -- nm_id
    'NIK-001',       -- vendor_code  
    'Nike',          -- brand
    'Футболка Nike Sport', -- title
    'Одежда',        -- subject
    0.1,             -- volume
    true             -- active
);

-- Баркоды (варианты)
INSERT INTO seller_articles VALUES 
(1, 12345, 'NIK-001', '1234567890123', 'M', true),   -- размер M
(2, 12345, 'NIK-001', '1234567890124', 'L', true),   -- размер L  
(3, 12345, 'NIK-001', '1234567890125', 'XL', true);  -- размер XL

-- Цены (одна цена на весь продукт)
INSERT INTO unit_economics VALUES (
    12345,           -- nm_id
    'NIK-001',       -- vendor_code
    1500.00,         -- price
    1350.00,         -- discounted_price
    10,              -- discount
    10,              -- discount_on_site
    1215.00,         -- price_after_spp
    1600.00,         -- competitive_price
    false,           -- is_competitive_price
    true             -- has_promotions
);
```

## 🎯 Логика обработки

### 1. Создание продукта
```python
# Из Discounts-Prices API получаем:
item = {
    'nmID': 12345,
    'vendorCode': 'NIK-001', 
    'brand': 'Nike',
    'title': 'Футболка Nike Sport',
    'subject': 'Одежда',
    'volume': 0.1,
    'barcodes': ['1234567890123', '1234567890124', '1234567890125'],
    'size': 'M',  # может быть массив размеров
    'prices': [1500],
    'discountedPrices': [1350],
    'discount': 10
}

# Обрабатываем:
processor = DiscountsPricesDBProcessor()
processed = processor.process_price_data(item)

# Результат:
{
    'nm_id': 12345,
    'vendor_code': 'NIK-001',
    'brand': 'Nike', 
    'title': 'Футболка Nike Sport',
    'subject': 'Одежда',
    'volume': 0.1,
    'variants': [
        {'barcode': '1234567890123', 'size': 'M', 'active': True},
        {'barcode': '1234567890124', 'size': 'L', 'active': True}, 
        {'barcode': '1234567890125', 'size': 'XL', 'active': True}
    ],
    'price': 1500.0,
    'discounted_price': 1350.0,
    'discount': 10,
    # ... остальные поля цен
}
```

### 2. Сохранение в БД
```python
# 1. Создаем продукт с вариантами
db_client.rpc('upsert_product_with_variants', {
    'p_nm_id': 12345,
    'p_vendor_code': 'NIK-001',
    'p_brand': 'Nike',
    'p_title': 'Футболка Nike Sport', 
    'p_subject': 'Одежда',
    'p_volume': 0.1,
    'p_variants': json.dumps([
        {'barcode': '1234567890123', 'size': 'M', 'active': True},
        {'barcode': '1234567890124', 'size': 'L', 'active': True},
        {'barcode': '1234567890125', 'size': 'XL', 'active': True}
    ])
}).execute()

# 2. Сохраняем цены
db_client.rpc('update_prices_with_history', {
    'p_nm_id': 12345,
    'p_vendor_code': 'NIK-001',
    'p_price': 1500.0,
    'p_discounted_price': 1350.0,
    'p_discount': 10,
    # ... остальные поля цен
}).execute()
```

## 📊 Запросы для анализа

### 1. Продукты с количеством баркодов
```sql
SELECT 
    p.nm_id,
    p.vendor_code,
    p.brand,
    p.title,
    COUNT(sa.id) as barcodes_count,
    COUNT(CASE WHEN sa.active = true THEN 1 END) as active_barcodes_count
FROM products p
LEFT JOIN seller_articles sa ON p.nm_id = sa.nm_id
WHERE p.active = true
GROUP BY p.nm_id, p.vendor_code, p.brand, p.title
ORDER BY barcodes_count DESC;
```

### 2. Полная информация о товаре
```sql
SELECT 
    p.nm_id,
    p.vendor_code,
    p.brand,
    p.title,
    p.subject,
    p.volume,
    sa.barcode,
    sa.size,
    sa.active as barcode_active,
    ue.price,
    ue.discounted_price,
    ue.discount
FROM products p
LEFT JOIN seller_articles sa ON p.nm_id = sa.nm_id
LEFT JOIN unit_economics ue ON p.nm_id = ue.nm_id
WHERE p.nm_id = 12345
ORDER BY sa.barcode;
```

### 3. Статистика по брендам
```sql
SELECT 
    brand,
    COUNT(DISTINCT p.nm_id) as products_count,
    COUNT(DISTINCT p.vendor_code) as vendor_codes_count,
    COUNT(sa.id) as barcodes_count
FROM products p
LEFT JOIN seller_articles sa ON p.nm_id = sa.nm_id
WHERE p.active = true AND brand IS NOT NULL
GROUP BY brand
ORDER BY products_count DESC;
```

## 🚀 Использование

### Тест иерархии
```bash
python database/test_product_hierarchy.py
```

### Синхронизация с правильной иерархией
```bash
python database/run_discounts_prices_sync.py --max-goods 100
```

### Программное использование
```python
from database.integrations.discounts_prices_enhanced import DiscountsPricesDBProcessor

processor = DiscountsPricesDBProcessor()

# Синхронизация
stats = processor.sync_prices_to_db(max_goods=1000)

# Обзор иерархии
overview = processor.get_products_overview()
print(f"Продуктов: {overview['hierarchy_summary']['products']['total_products']}")
print(f"Баркодов: {overview['hierarchy_summary']['barcodes']['total_barcodes']}")
```

## ✅ Преимущества такой структуры

1. **Гибкость**: Один продукт может иметь множество размеров/цветов
2. **Масштабируемость**: Легко добавлять новые варианты
3. **Целостность**: Цены привязаны к продукту, а не к баркоду
4. **Аналитика**: Возможность анализа на разных уровнях
5. **Производительность**: Индексы по всем ключевым полям
6. **История**: Полная история изменений цен по продуктам
