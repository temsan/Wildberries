# 📦 Конфигурация хранения артикулов

## 🎯 Бизнес-логика Макара

### Иерархия товаров:
```
АРТИКУЛ (nmID) - основной уровень управления
    ├── Артикул продавца (vendorCode) - дополнительная информация
    └── БАРКОДЫ = РАЗМЕРЫ (M, L, XL) - дискретные единицы
```

### Принципы управления:
- **Управление**: По артикулу (nmID) целиком
- **Закупки**: По артикулу (каких-то больше, каких-то меньше)
- **Настройки размеров**: Редко используются
- **Цены**: Общие для всех размеров артикула

## 🏗️ Структура БД

### 1. PRODUCTS (основная таблица артикулов)
```sql
CREATE TABLE products (
    id BIGSERIAL PRIMARY KEY,
    nm_id INTEGER NOT NULL UNIQUE,           -- Артикул WB (основной идентификатор)
    vendor_code VARCHAR(255) NOT NULL,       -- Артикул продавца (дополнение)
    brand VARCHAR(255),                      -- Бренд
    title TEXT,                              -- Название товара
    subject VARCHAR(255),                    -- Категория/класс товара
    volume DECIMAL(10,3),                    -- Объем упаковки (л)
    active BOOLEAN DEFAULT true,             -- Активность товара
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Назначение**: Основная таблица для управления товарами по артикулу (nmID)

### 2. SELLER_ARTICLES (размеры/баркоды)
```sql
CREATE TABLE seller_articles (
    id BIGSERIAL PRIMARY KEY,
    nm_id INTEGER NOT NULL REFERENCES products(nm_id), -- Связь с артикулом
    vendor_code VARCHAR(255) NOT NULL,                  -- Дублирование для быстрого доступа
    barcode VARCHAR(255) NOT NULL UNIQUE,               -- Штрихкод = размер (M, L, XL)
    size VARCHAR(100),                                  -- Размер товара
    active BOOLEAN DEFAULT true,                        -- Активность размера
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Назначение**: Дискретные единицы товара (размеры), связанные с артикулом

## 📊 Тип хранения: ПРОСТОЕ ОБНОВЛЕНИЕ

### ✅ Что обновляется (без истории):
- **Артикул (nmID)** - статический идентификатор
- **Артикул продавца (vendorCode)** - редко меняется
- **Баркод** - статический идентификатор размера
- **Размер** - постоянный атрибут
- **Название** - текущая версия
- **Категория WB** - текущая категория
- **Бренд** - текущий бренд
- **Объем** - текущий объем

### 🔄 Что НЕ хранится как временные ряды:
- История изменений названий
- История изменений категорий
- История изменений брендов
- История изменений размеров

## 🎯 Логика обработки данных

### 1. Создание/обновление артикула:
```python
# Основной артикул (nmID)
product_data = {
    'nm_id': 12345,
    'vendor_code': 'NIK-001',
    'brand': 'Nike',
    'title': 'Футболка Nike Sport',
    'subject': 'Одежда',
    'volume': 0.1
}

# Размеры/баркоды для этого артикула
variants = [
    {'barcode': '1234567890123', 'size': 'M'},
    {'barcode': '1234567890124', 'size': 'L'},
    {'barcode': '1234567890125', 'size': 'XL'}
]
```

### 2. Функция upsert:
```sql
-- Создает/обновляет артикул и все его размеры
SELECT upsert_product_with_variants(
    p_nm_id := 12345,
    p_vendor_code := 'NIK-001',
    p_brand := 'Nike',
    p_title := 'Футболка Nike Sport',
    p_subject := 'Одежда',
    p_volume := 0.1,
    p_variants := '[
        {"barcode": "1234567890123", "size": "M", "active": true},
        {"barcode": "1234567890124", "size": "L", "active": true},
        {"barcode": "1234567890125", "size": "XL", "active": true}
    ]'::jsonb
);
```

## 📈 Запросы для управления

### 1. Получить артикул со всеми размерами:
```sql
SELECT 
    p.nm_id,
    p.vendor_code,
    p.brand,
    p.title,
    sa.barcode,
    sa.size,
    sa.active
FROM products p
LEFT JOIN seller_articles sa ON p.nm_id = sa.nm_id
WHERE p.nm_id = 12345
ORDER BY sa.size;
```

### 2. Статистика по артикулам:
```sql
SELECT 
    COUNT(*) as total_articles,
    COUNT(DISTINCT p.nm_id) as unique_articles,
    COUNT(sa.id) as total_sizes,
    AVG(size_count.sizes_per_article) as avg_sizes_per_article
FROM products p
LEFT JOIN seller_articles sa ON p.nm_id = sa.nm_id
LEFT JOIN (
    SELECT nm_id, COUNT(*) as sizes_per_article
    FROM seller_articles
    GROUP BY nm_id
) size_count ON p.nm_id = size_count.nm_id;
```

### 3. Топ артикулов по количеству размеров:
```sql
SELECT 
    p.nm_id,
    p.vendor_code,
    p.brand,
    p.title,
    COUNT(sa.id) as sizes_count
FROM products p
LEFT JOIN seller_articles sa ON p.nm_id = sa.nm_id
WHERE p.active = true
GROUP BY p.nm_id, p.vendor_code, p.brand, p.title
ORDER BY sizes_count DESC
LIMIT 20;
```

## 🔧 Настройка интеграции

### В DiscountsPricesDBProcessor:
```python
def _extract_variants(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Извлекает варианты товара (баркоды = размеры).
    
    Бизнес-логика:
    - Баркод = Размер товара (M, L, XL)
    - Управление = По артикулу (nmID) целиком
    - Цены = Общие для всех размеров
    """
    variants = []
    
    # Получаем баркоды из API
    barcodes = item.get('barcodes', [])
    if not barcodes:
        barcodes = item.get('barcode', [])
    
    # Обрабатываем каждый баркод как отдельный размер
    for i, barcode in enumerate(barcodes):
        if barcode and str(barcode).strip():
            # Определяем размер
            size = self._determine_size(item, i)
            
            variant = {
                'barcode': str(barcode).strip(),
                'size': size,
                'active': True
            }
            variants.append(variant)
    
    return variants

def _determine_size(self, item: Dict[str, Any], index: int) -> str:
    """Определяет размер для баркода."""
    sizes = item.get('sizes', [])
    if sizes and index < len(sizes):
        return sizes[index]
    
    # Генерируем размер по индексу
    size_options = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
    return size_options[index] if index < len(size_options) else f'Size_{index+1}'
```

## 🎯 Преимущества такой конфигурации:

1. **Простота управления** - все операции по артикулу (nmID)
2. **Экономия места** - нет истории изменений справочников
3. **Быстрые запросы** - индексы по ключевым полям
4. **Гибкость размеров** - легко добавлять/удалять размеры
5. **Соответствие бизнес-логике** - как работает Макар

## 🚀 Использование:

### Синхронизация артикулов:
```bash
python database/run_discounts_prices_sync.py --max-goods 100
```

### Тест иерархии:
```bash
python database/test_product_hierarchy.py
```

### Веб-интерфейс:
```bash
python database/web_interface.py
# Открыть: http://localhost:8501
```
