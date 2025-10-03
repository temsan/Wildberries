-- ============================================================================
-- ПРИМЕРЫ SQL-ЗАПРОСОВ ДЛЯ ИНТЕГРАЦИИ С PYTHON
-- ============================================================================
-- Готовые запросы для использования в Python-коде проекта WB API
-- ============================================================================

-- ============================================================================
-- 1. UPSERT АРТИКУЛОВ ИЗ CONTENT API (list_of_seller_articles)
-- ============================================================================

-- 1.1. Простой upsert одного товара
-- Использование: после получения данных из content_cards API
INSERT INTO products (nm_id, vendor_code, brand, title, subject, volume)
VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT (nm_id) DO UPDATE SET
    vendor_code = EXCLUDED.vendor_code,
    brand = EXCLUDED.brand,
    title = EXCLUDED.title,
    subject = EXCLUDED.subject,
    volume = EXCLUDED.volume,
    updated_at = NOW()
RETURNING id, nm_id;

-- 1.2. Batch upsert артикулов (эффективнее для больших объемов)
-- Python: executemany или COPY
INSERT INTO products (nm_id, vendor_code, brand, title, subject, volume)
VALUES 
    (12345678, 'ART-001', 'MyBrand', 'Товар 1', 'Футболки', 0.5),
    (23456789, 'ART-002', 'MyBrand', 'Товар 2', 'Кроссовки', 1.2)
ON CONFLICT (nm_id) DO UPDATE SET
    vendor_code = EXCLUDED.vendor_code,
    brand = EXCLUDED.brand,
    title = EXCLUDED.title,
    subject = EXCLUDED.subject,
    volume = EXCLUDED.volume,
    updated_at = NOW();

-- 1.3. Upsert варианта артикула (баркод + размер)
-- Для каждого barcode из sizes[].skus
INSERT INTO seller_articles (nm_id, vendor_code, barcode, size)
VALUES ($1, $2, $3, $4)
ON CONFLICT (barcode) DO UPDATE SET
    nm_id = EXCLUDED.nm_id,
    vendor_code = EXCLUDED.vendor_code,
    size = EXCLUDED.size,
    updated_at = NOW()
RETURNING id, barcode;

-- 1.4. Batch upsert баркодов
INSERT INTO seller_articles (nm_id, vendor_code, barcode, size)
VALUES 
    (12345678, 'ART-001', '2000000123456', 'M'),
    (12345678, 'ART-001', '2000000123457', 'L'),
    (23456789, 'ART-002', '2000000234567', '42')
ON CONFLICT (barcode) DO UPDATE SET
    nm_id = EXCLUDED.nm_id,
    vendor_code = EXCLUDED.vendor_code,
    size = EXCLUDED.size,
    updated_at = NOW();

-- 1.5. Использование функции upsert_product_with_variants
-- Вставка товара со всеми его вариантами одним вызовом
SELECT upsert_product_with_variants(
    12345678, -- nm_id
    'ART-001', -- vendor_code
    'MyBrand', -- brand
    'Футболка летняя', -- title
    'Футболки', -- subject
    0.5, -- volume
    '[
        {"barcode": "2000000123456", "size": "M"},
        {"barcode": "2000000123457", "size": "L"},
        {"barcode": "2000000123458", "size": "XL"}
    ]'::jsonb -- variants
);

-- ============================================================================
-- 2. UPSERT ЦЕН ИЗ DISCOUNTS-PRICES API
-- ============================================================================

-- 2.1. Простой upsert цен для одного товара
INSERT INTO unit_economics (
    nm_id, vendor_code, price, discounted_price, discount, 
    discount_on_site, price_after_spp, competitive_price, 
    is_competitive_price, has_promotions
)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
ON CONFLICT (nm_id) DO UPDATE SET
    vendor_code = EXCLUDED.vendor_code,
    price = EXCLUDED.price,
    discounted_price = EXCLUDED.discounted_price,
    discount = EXCLUDED.discount,
    discount_on_site = EXCLUDED.discount_on_site,
    price_after_spp = EXCLUDED.price_after_spp,
    competitive_price = EXCLUDED.competitive_price,
    is_competitive_price = EXCLUDED.is_competitive_price,
    has_promotions = EXCLUDED.has_promotions,
    updated_at = NOW()
RETURNING nm_id, price_after_spp;

-- 2.2. Batch upsert цен (для больших объемов)
INSERT INTO unit_economics (
    nm_id, vendor_code, price, discounted_price, discount, 
    discount_on_site, price_after_spp, competitive_price, 
    is_competitive_price, has_promotions
)
VALUES 
    (12345678, 'ART-001', 1500.00, 1200.00, 20, 10, 1080.00, 1050.00, true, false),
    (23456789, 'ART-002', 3000.00, 2400.00, 20, 15, 2040.00, 99999, false, true)
ON CONFLICT (nm_id) DO UPDATE SET
    vendor_code = EXCLUDED.vendor_code,
    price = EXCLUDED.price,
    discounted_price = EXCLUDED.discounted_price,
    discount = EXCLUDED.discount,
    discount_on_site = EXCLUDED.discount_on_site,
    price_after_spp = EXCLUDED.price_after_spp,
    competitive_price = EXCLUDED.competitive_price,
    is_competitive_price = EXCLUDED.is_competitive_price,
    has_promotions = EXCLUDED.has_promotions,
    updated_at = NOW();

-- 2.3. Использование функции с автоматическим сохранением в историю
-- Автоматически сохраняет старые значения в price_history перед обновлением
SELECT update_prices_with_history(
    12345678, -- nm_id
    'ART-001', -- vendor_code
    1500.00, -- price
    1200.00, -- discounted_price
    20, -- discount
    10, -- discount_on_site
    1080.00, -- price_after_spp
    1050.00, -- competitive_price
    true, -- is_competitive_price
    false -- has_promotions
);

-- ============================================================================
-- 3. ВЫБОРКА АКТИВНЫХ АРТИКУЛОВ ДЛЯ ЭКСПОРТА В GOOGLE SHEETS
-- ============================================================================

-- 3.1. Все активные артикулы с ценами (для таблицы "Юнит-экономика")
SELECT 
    sa.nm_id AS "Артикул WB",
    sa.vendor_code AS "Артикул продавца",
    sa.barcode AS "Штрихкод",
    sa.size AS "Размер",
    p.brand AS "Бренд",
    p.title AS "Название",
    p.subject AS "Категория",
    p.volume AS "Литраж",
    ue.price AS "Цена",
    ue.discounted_price AS "Цена со скидкой",
    ue.discount AS "Скидка (%)",
    ue.discount_on_site AS "СПП (%)",
    ue.price_after_spp AS "Цена после СПП",
    ue.competitive_price AS "Привлекательная цена",
    ue.is_competitive_price AS "Конкурентная?",
    ue.has_promotions AS "Есть промо?"
FROM seller_articles sa
JOIN products p ON sa.nm_id = p.nm_id
LEFT JOIN unit_economics ue ON sa.nm_id = ue.nm_id
WHERE sa.active = true AND p.active = true
ORDER BY sa.nm_id, sa.barcode;

-- 3.2. Только товары с установленными ценами
SELECT 
    p.nm_id,
    p.vendor_code,
    p.brand,
    p.title,
    ue.price,
    ue.discounted_price,
    ue.price_after_spp,
    ue.updated_at AS "Дата обновления цен"
FROM products p
JOIN unit_economics ue ON p.nm_id = ue.nm_id
WHERE p.active = true 
    AND ue.price IS NOT NULL
ORDER BY ue.updated_at DESC;

-- 3.3. Использование view для экспорта
SELECT * FROM v_active_articles_export;

-- 3.4. Товары с изменениями цен за последние N дней
SELECT 
    p.nm_id,
    p.vendor_code,
    p.brand,
    ue.price,
    ue.discounted_price,
    ue.discount,
    ue.price_after_spp,
    ue.updated_at
FROM products p
JOIN unit_economics ue ON p.nm_id = ue.nm_id
WHERE p.active = true 
    AND ue.updated_at >= NOW() - INTERVAL '7 days'
ORDER BY ue.updated_at DESC;

-- ============================================================================
-- 4. РАБОТА С ОСТАТКАМИ НА СКЛАДАХ (warehouse_remains)
-- ============================================================================

-- 4.1. Upsert остатков для баркода на конкретном складе
INSERT INTO warehouse_remains (
    barcode, nm_id, vendor_code, warehouse_name, quantity,
    in_way_to_recipients, in_way_returns_to_warehouse, snapshot_date
)
VALUES ($1, $2, $3, $4, $5, $6, $7, CURRENT_DATE)
ON CONFLICT (barcode, warehouse_name, snapshot_date) DO UPDATE SET
    quantity = EXCLUDED.quantity,
    in_way_to_recipients = EXCLUDED.in_way_to_recipients,
    in_way_returns_to_warehouse = EXCLUDED.in_way_returns_to_warehouse,
    created_at = NOW()
RETURNING id;

-- 4.2. Batch upsert остатков (агрегированные данные с warehouse_remains API)
INSERT INTO warehouse_remains (
    barcode, nm_id, vendor_code, warehouse_name, quantity,
    in_way_to_recipients, in_way_returns_to_warehouse, snapshot_date
)
VALUES 
    ('2000000123456', 12345678, 'ART-001', 'Коледино', 150, 20, 5, CURRENT_DATE),
    ('2000000123456', 12345678, 'ART-001', 'Подольск', 230, 15, 3, CURRENT_DATE),
    ('2000000123457', 12345678, 'ART-001', 'Коледино', 80, 10, 2, CURRENT_DATE)
ON CONFLICT (barcode, warehouse_name, snapshot_date) DO UPDATE SET
    quantity = EXCLUDED.quantity,
    in_way_to_recipients = EXCLUDED.in_way_to_recipients,
    in_way_returns_to_warehouse = EXCLUDED.in_way_returns_to_warehouse;

-- 4.3. Получить остатки по всем складам для товара
SELECT 
    wr.warehouse_name AS "Склад",
    wr.quantity AS "Количество",
    wr.in_way_to_recipients AS "В пути к клиенту",
    wr.in_way_returns_to_warehouse AS "В пути возврат"
FROM warehouse_remains wr
WHERE wr.nm_id = $1 
    AND wr.snapshot_date = CURRENT_DATE
ORDER BY wr.warehouse_name;

-- 4.4. Агрегация остатков по артикулу (все баркоды, все склады)
SELECT 
    wr.nm_id,
    p.vendor_code,
    p.brand,
    SUM(wr.quantity) AS "Всего на складах",
    SUM(wr.in_way_to_recipients) AS "Всего в пути к клиенту",
    SUM(wr.in_way_returns_to_warehouse) AS "Всего в пути возврат",
    COUNT(DISTINCT wr.warehouse_name) AS "Количество складов"
FROM warehouse_remains wr
JOIN products p ON wr.nm_id = p.nm_id
WHERE wr.snapshot_date = CURRENT_DATE
GROUP BY wr.nm_id, p.vendor_code, p.brand
ORDER BY "Всего на складах" DESC;

-- 4.5. История остатков по товару за последние 14 дней
SELECT 
    wr.snapshot_date AS "Дата",
    SUM(wr.quantity) AS "Остаток",
    SUM(wr.in_way_to_recipients) AS "В пути"
FROM warehouse_remains wr
WHERE wr.nm_id = $1
    AND wr.snapshot_date >= CURRENT_DATE - INTERVAL '14 days'
GROUP BY wr.snapshot_date
ORDER BY wr.snapshot_date DESC;

-- ============================================================================
-- 5. ВАЛИДАЦИЯ И ЛОГИРОВАНИЕ
-- ============================================================================

-- 5.1. Добавить лог валидации
INSERT INTO validation_logs (
    operation_type, status, input_data, validation_errors,
    records_processed, records_failed, execution_time_ms
)
VALUES (
    'fetch_prices', -- operation_type
    'success', -- status: success, warning, error
    '{"sample": {"nmID": 12345678, "price": 1500}}'::jsonb, -- input_data
    NULL, -- validation_errors (NULL если успех)
    150, -- records_processed
    0, -- records_failed
    2500 -- execution_time_ms
)
RETURNING id, timestamp;

-- 5.2. Добавить лог с ошибками валидации
INSERT INTO validation_logs (
    operation_type, status, input_data, validation_errors,
    records_processed, records_failed, execution_time_ms
)
VALUES (
    'fetch_articles',
    'warning',
    '{"sample": {"nmID": 12345678}}'::jsonb,
    '[
        {"nmID": 12345678, "error": "Missing vendorCode", "severity": "warning"},
        {"nmID": 23456789, "error": "Invalid barcode format", "severity": "error"}
    ]'::jsonb,
    100,
    2,
    1800
);

-- 5.3. Получить последние логи с ошибками
SELECT 
    operation_type,
    status,
    records_processed,
    records_failed,
    validation_errors,
    timestamp
FROM validation_logs
WHERE status IN ('warning', 'error')
ORDER BY timestamp DESC
LIMIT 20;

-- 5.4. Статистика валидации за последние 7 дней
SELECT 
    operation_type,
    status,
    COUNT(*) AS executions,
    SUM(records_processed) AS total_records,
    SUM(records_failed) AS total_failed,
    AVG(execution_time_ms) AS avg_execution_ms,
    MAX(timestamp) AS last_run
FROM validation_logs
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY operation_type, status
ORDER BY operation_type, status;

-- ============================================================================
-- 6. АНАЛИТИЧЕСКИЕ ЗАПРОСЫ
-- ============================================================================

-- 6.1. Топ товаров по скидкам
SELECT 
    p.nm_id,
    p.vendor_code,
    p.brand,
    p.title,
    ue.price,
    ue.discounted_price,
    ue.discount,
    (ue.price - ue.discounted_price) AS "Сумма скидки"
FROM products p
JOIN unit_economics ue ON p.nm_id = ue.nm_id
WHERE p.active = true 
    AND ue.discount > 0
ORDER BY ue.discount DESC
LIMIT 50;

-- 6.2. Товары с конкурентной ценой
SELECT 
    p.nm_id,
    p.vendor_code,
    p.brand,
    ue.price_after_spp,
    ue.competitive_price,
    (ue.competitive_price - ue.price_after_spp) AS "Разница с конкурентной"
FROM products p
JOIN unit_economics ue ON p.nm_id = ue.nm_id
WHERE p.active = true 
    AND ue.is_competitive_price = true
    AND ue.competitive_price != 99999
ORDER BY "Разница с конкурентной" DESC;

-- 6.3. Анализ изменения цен (история за 30 дней)
SELECT 
    ph.nm_id,
    p.vendor_code,
    p.brand,
    COUNT(*) AS "Изменений",
    MIN(ph.price_after_spp) AS "Мин. цена",
    MAX(ph.price_after_spp) AS "Макс. цена",
    AVG(ph.price_after_spp) AS "Средняя цена",
    MAX(ph.recorded_at) AS "Последнее изменение"
FROM price_history ph
JOIN products p ON ph.nm_id = p.nm_id
WHERE ph.recorded_at >= NOW() - INTERVAL '30 days'
GROUP BY ph.nm_id, p.vendor_code, p.brand
HAVING COUNT(*) > 1
ORDER BY "Изменений" DESC
LIMIT 30;

-- 6.4. Товары без обновления цен > 7 дней
SELECT 
    p.nm_id,
    p.vendor_code,
    p.brand,
    p.title,
    ue.updated_at,
    NOW() - ue.updated_at AS "Прошло времени"
FROM products p
JOIN unit_economics ue ON p.nm_id = ue.nm_id
WHERE p.active = true
    AND ue.updated_at < NOW() - INTERVAL '7 days'
ORDER BY ue.updated_at ASC;

-- 6.5. Статистика по брендам
SELECT 
    p.brand,
    COUNT(DISTINCT p.nm_id) AS "Товаров",
    COUNT(DISTINCT sa.barcode) AS "Баркодов",
    AVG(ue.price) AS "Средняя цена",
    AVG(ue.discount) AS "Средняя скидка",
    SUM(CASE WHEN ue.is_competitive_price THEN 1 ELSE 0 END) AS "С конкурентной ценой"
FROM products p
LEFT JOIN seller_articles sa ON p.nm_id = sa.nm_id
LEFT JOIN unit_economics ue ON p.nm_id = ue.nm_id
WHERE p.active = true
GROUP BY p.brand
ORDER BY "Товаров" DESC;

-- ============================================================================
-- 7. ОБСЛУЖИВАНИЕ И МОНИТОРИНГ
-- ============================================================================

-- 7.1. Очистка старых логов (старше 30 дней)
SELECT cleanup_old_logs();

-- 7.2. Очистка старой истории цен (старше 90 дней)
SELECT cleanup_old_price_history();

-- 7.3. Статистика по таблицам
SELECT 
    'products' AS table_name,
    COUNT(*) AS total_records,
    COUNT(*) FILTER (WHERE active = true) AS active_records,
    MAX(updated_at) AS last_update
FROM products
UNION ALL
SELECT 
    'seller_articles',
    COUNT(*),
    COUNT(*) FILTER (WHERE active = true),
    MAX(updated_at)
FROM seller_articles
UNION ALL
SELECT 
    'unit_economics',
    COUNT(*),
    COUNT(*) FILTER (WHERE price IS NOT NULL),
    MAX(updated_at)
FROM unit_economics
UNION ALL
SELECT 
    'warehouse_remains',
    COUNT(*),
    COUNT(DISTINCT nm_id),
    MAX(created_at)
FROM warehouse_remains;

-- 7.4. Проверка целостности данных
-- Товары без баркодов
SELECT 
    p.nm_id,
    p.vendor_code,
    p.brand,
    COUNT(sa.id) AS barcode_count
FROM products p
LEFT JOIN seller_articles sa ON p.nm_id = sa.nm_id AND sa.active = true
WHERE p.active = true
GROUP BY p.nm_id, p.vendor_code, p.brand
HAVING COUNT(sa.id) = 0;

-- Баркоды без связи с товарами
SELECT 
    sa.barcode,
    sa.nm_id,
    sa.vendor_code
FROM seller_articles sa
LEFT JOIN products p ON sa.nm_id = p.nm_id
WHERE p.id IS NULL;

-- Товары с ценами без баркодов
SELECT 
    ue.nm_id,
    ue.vendor_code,
    ue.price,
    COUNT(sa.id) AS barcode_count
FROM unit_economics ue
LEFT JOIN seller_articles sa ON ue.nm_id = sa.nm_id
GROUP BY ue.nm_id, ue.vendor_code, ue.price
HAVING COUNT(sa.id) = 0;

-- ============================================================================
-- 8. ТРАНЗАКЦИОННЫЕ ОПЕРАЦИИ (примеры для Python)
-- ============================================================================

-- 8.1. Атомарное обновление товара с вариантами и ценами
BEGIN;

-- Шаг 1: Upsert товара
INSERT INTO products (nm_id, vendor_code, brand, title, subject, volume)
VALUES (12345678, 'ART-001', 'MyBrand', 'Товар 1', 'Футболки', 0.5)
ON CONFLICT (nm_id) DO UPDATE SET
    vendor_code = EXCLUDED.vendor_code,
    brand = EXCLUDED.brand,
    title = EXCLUDED.title,
    subject = EXCLUDED.subject,
    volume = EXCLUDED.volume,
    updated_at = NOW();

-- Шаг 2: Upsert баркодов
INSERT INTO seller_articles (nm_id, vendor_code, barcode, size)
VALUES 
    (12345678, 'ART-001', '2000000123456', 'M'),
    (12345678, 'ART-001', '2000000123457', 'L')
ON CONFLICT (barcode) DO UPDATE SET
    nm_id = EXCLUDED.nm_id,
    vendor_code = EXCLUDED.vendor_code,
    size = EXCLUDED.size,
    updated_at = NOW();

-- Шаг 3: Upsert цен
INSERT INTO unit_economics (
    nm_id, vendor_code, price, discounted_price, discount, 
    discount_on_site, price_after_spp, competitive_price, 
    is_competitive_price, has_promotions
)
VALUES (12345678, 'ART-001', 1500.00, 1200.00, 20, 10, 1080.00, 1050.00, true, false)
ON CONFLICT (nm_id) DO UPDATE SET
    price = EXCLUDED.price,
    discounted_price = EXCLUDED.discounted_price,
    discount = EXCLUDED.discount,
    discount_on_site = EXCLUDED.discount_on_site,
    price_after_spp = EXCLUDED.price_after_spp,
    competitive_price = EXCLUDED.competitive_price,
    is_competitive_price = EXCLUDED.is_competitive_price,
    has_promotions = EXCLUDED.has_promotions,
    updated_at = NOW();

-- Шаг 4: Логирование
INSERT INTO validation_logs (
    operation_type, status, records_processed, records_failed
)
VALUES ('full_product_update', 'success', 1, 0);

COMMIT;

-- ============================================================================
-- ПРИМЕЧАНИЯ ПО ИСПОЛЬЗОВАНИЮ В PYTHON
-- ============================================================================
/*
1. Используйте prepared statements для защиты от SQL injection:
   cursor.execute("INSERT INTO products ... VALUES ($1, $2, $3)", (nm_id, vendor, brand))

2. Для batch операций используйте executemany() или COPY:
   cursor.executemany("INSERT INTO products ... VALUES ($1, $2, $3)", data_list)

3. Используйте транзакции для связанных операций:
   with conn:
       with conn.cursor() as cur:
           cur.execute("INSERT INTO products ...")
           cur.execute("INSERT INTO seller_articles ...")

4. Для экспорта в Google Sheets используйте views или готовые запросы:
   cur.execute("SELECT * FROM v_active_articles_export")
   data = cur.fetchall()

5. Логируйте все операции:
   cur.execute("INSERT INTO validation_logs ...")
*/

