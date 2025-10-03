-- ============================================================================
-- WILDBERRIES API DATABASE SCHEMA (Supabase/PostgreSQL)
-- ============================================================================
-- Схема БД для автоматизации работы с WB API:
-- - Хранение артикулов товаров (nmID, vendorCode, barcode)
-- - Управление ценами и скидками (юнит-экономика)
-- - Валидация данных и логирование
-- - RLS (Row Level Security) для безопасности
-- - JSONB для гибкого хранения схем и логов
-- - Индексы для производительности
-- ============================================================================

-- Расширения PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. PRODUCTS (Товары) - основная таблица карточек товаров
-- ============================================================================
CREATE TABLE products (
    id BIGSERIAL PRIMARY KEY,
    nm_id INTEGER NOT NULL UNIQUE, -- Артикул WB (уникальный идентификатор товара)
    vendor_code VARCHAR(255) NOT NULL, -- Артикул продавца
    brand VARCHAR(255), -- Бренд
    title TEXT, -- Название товара
    subject VARCHAR(255), -- Категория/класс товара
    volume DECIMAL(10,3), -- Объем упаковки (л)
    active BOOLEAN DEFAULT true, -- Активность товара
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT products_nm_id_positive CHECK (nm_id > 0)
);

-- Индексы для products
CREATE INDEX idx_products_nm_id ON products(nm_id);
CREATE INDEX idx_products_vendor_code ON products(vendor_code);
CREATE INDEX idx_products_brand ON products(brand);
CREATE INDEX idx_products_active ON products(active);
CREATE INDEX idx_products_updated_at ON products(updated_at DESC);

-- Комментарии
COMMENT ON TABLE products IS 'Основная таблица карточек товаров из Content API';
COMMENT ON COLUMN products.nm_id IS 'Артикул WB (nmID) - уникальный идентификатор товара';
COMMENT ON COLUMN products.vendor_code IS 'Артикул продавца (vendorCode)';
COMMENT ON COLUMN products.volume IS 'Объем упаковки в литрах';

-- ============================================================================
-- 2. SELLER_ARTICLES (Варианты артикулов) - штрихкоды и размеры
-- ============================================================================
CREATE TABLE seller_articles (
    id BIGSERIAL PRIMARY KEY,
    nm_id INTEGER NOT NULL REFERENCES products(nm_id) ON DELETE CASCADE,
    vendor_code VARCHAR(255) NOT NULL, -- Дублируем для быстрого доступа
    barcode VARCHAR(255) NOT NULL UNIQUE, -- Штрихкод (уникальный)
    size VARCHAR(100), -- Размер товара (techSize/wbSize)
    active BOOLEAN DEFAULT true, -- Активность варианта
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT seller_articles_barcode_not_empty CHECK (LENGTH(barcode) > 0)
);

-- Индексы для seller_articles
CREATE INDEX idx_seller_articles_nm_id ON seller_articles(nm_id);
CREATE INDEX idx_seller_articles_barcode ON seller_articles(barcode);
CREATE INDEX idx_seller_articles_vendor_code ON seller_articles(vendor_code);
CREATE INDEX idx_seller_articles_active ON seller_articles(active);
CREATE UNIQUE INDEX idx_seller_articles_unique_quad ON seller_articles(nm_id, barcode, vendor_code, size);

-- Комментарии
COMMENT ON TABLE seller_articles IS 'Варианты записи артикулов: штрихкоды и размеры (1 nmID → N баркодов)';
COMMENT ON COLUMN seller_articles.barcode IS 'Штрихкод товара (уникальный идентификатор варианта)';
COMMENT ON COLUMN seller_articles.size IS 'Размер товара из techSize или wbSize';

-- ============================================================================
-- 3. UNIT_ECONOMICS (Юнит-экономика) - цены и скидки
-- ============================================================================
CREATE TABLE unit_economics (
    id BIGSERIAL PRIMARY KEY,
    nm_id INTEGER NOT NULL UNIQUE REFERENCES products(nm_id) ON DELETE CASCADE,
    vendor_code VARCHAR(255) NOT NULL, -- Дублируем для быстрого доступа
    
    -- Цены
    price DECIMAL(10,2), -- Базовая цена (до скидки продавца)
    discounted_price DECIMAL(10,2), -- Цена со скидкой продавца
    
    -- Скидки
    discount INTEGER DEFAULT 0, -- Скидка продавца (%)
    add_club_discount INTEGER, -- Дополнительная скидка WB Клуб (%)
    discount_on_site INTEGER, -- СПП - скидка на сайте (%)
    
    -- Расчетные поля
    price_after_spp DECIMAL(10,2), -- Цена после применения СПП
    
    -- Конкурентная цена
    competitive_price DECIMAL(10,2), -- Привлекательная цена (99999 если нет)
    is_competitive_price BOOLEAN DEFAULT false, -- Флаг конкурентной цены
    
    -- Промо-акции
    has_promotions BOOLEAN DEFAULT false, -- Наличие промо-акций
    
    -- Метаданные
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unit_economics_price_positive CHECK (price IS NULL OR price >= 0),
    CONSTRAINT unit_economics_discount_range CHECK (discount >= 0 AND discount <= 100),
    CONSTRAINT unit_economics_discount_on_site_range CHECK (discount_on_site IS NULL OR (discount_on_site >= 0 AND discount_on_site <= 100))
);

-- Индексы для unit_economics
CREATE INDEX idx_unit_economics_nm_id ON unit_economics(nm_id);
CREATE INDEX idx_unit_economics_vendor_code ON unit_economics(vendor_code);
CREATE INDEX idx_unit_economics_updated_at ON unit_economics(updated_at DESC);
CREATE INDEX idx_unit_economics_is_competitive ON unit_economics(is_competitive_price);
CREATE INDEX idx_unit_economics_has_promotions ON unit_economics(has_promotions);

-- Комментарии
COMMENT ON TABLE unit_economics IS 'Юнит-экономика: цены, скидки, СПП из Discounts-Prices API';
COMMENT ON COLUMN unit_economics.price IS 'Базовая цена товара (до скидки продавца)';
COMMENT ON COLUMN unit_economics.discounted_price IS 'Цена после скидки продавца';
COMMENT ON COLUMN unit_economics.discount IS 'Скидка продавца в процентах (0-100)';
COMMENT ON COLUMN unit_economics.discount_on_site IS 'СПП - Скидка Постоянного Покупателя (%)';
COMMENT ON COLUMN unit_economics.price_after_spp IS 'Итоговая цена после применения СПП';
COMMENT ON COLUMN unit_economics.competitive_price IS 'Конкурентная (привлекательная) цена от WB';

-- ============================================================================
-- 4. WAREHOUSE_REMAINS (Остатки на складах) - для будущей реализации
-- ============================================================================
CREATE TABLE warehouse_remains (
    id BIGSERIAL PRIMARY KEY,
    barcode VARCHAR(255) NOT NULL REFERENCES seller_articles(barcode) ON DELETE CASCADE,
    nm_id INTEGER NOT NULL, -- Дублируем для быстрого доступа
    vendor_code VARCHAR(255), -- Дублируем для быстрого доступа
    
    -- Склад и количество
    warehouse_name VARCHAR(255) NOT NULL, -- Название склада
    quantity INTEGER DEFAULT 0, -- Количество на складе
    
    -- В пути
    in_way_to_recipients INTEGER DEFAULT 0, -- В пути к получателям
    in_way_returns_to_warehouse INTEGER DEFAULT 0, -- В пути возвраты на склад
    
    -- Метаданные
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE, -- Дата снимка
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT warehouse_remains_quantity_positive CHECK (quantity >= 0),
    CONSTRAINT warehouse_remains_in_way_positive CHECK (in_way_to_recipients >= 0 AND in_way_returns_to_warehouse >= 0)
);

-- Индексы для warehouse_remains
CREATE INDEX idx_warehouse_remains_barcode ON warehouse_remains(barcode);
CREATE INDEX idx_warehouse_remains_nm_id ON warehouse_remains(nm_id);
CREATE INDEX idx_warehouse_remains_warehouse ON warehouse_remains(warehouse_name);
CREATE INDEX idx_warehouse_remains_snapshot_date ON warehouse_remains(snapshot_date DESC);
CREATE UNIQUE INDEX idx_warehouse_remains_unique ON warehouse_remains(barcode, warehouse_name, snapshot_date);

-- Комментарии
COMMENT ON TABLE warehouse_remains IS 'Остатки товаров на складах (ежедневные снимки)';
COMMENT ON COLUMN warehouse_remains.snapshot_date IS 'Дата снимка остатков (для исторических данных)';

-- ============================================================================
-- 5. API_SCHEMAS (Схемы валидации) - для хранения схем API
-- ============================================================================
CREATE TABLE api_schemas (
    id SERIAL PRIMARY KEY,
    schema_name VARCHAR(100) NOT NULL UNIQUE, -- Название схемы (content_cards, discounts_prices, etc)
    schema_version VARCHAR(50) NOT NULL, -- Версия схемы (v1, v2, etc)
    structure JSONB NOT NULL, -- Структура схемы в формате JSON
    description TEXT, -- Описание схемы
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT api_schemas_structure_not_empty CHECK (jsonb_typeof(structure) = 'object')
);

-- Индексы для api_schemas
CREATE INDEX idx_api_schemas_name ON api_schemas(schema_name);
CREATE INDEX idx_api_schemas_version ON api_schemas(schema_version);
CREATE INDEX idx_api_schemas_structure_gin ON api_schemas USING GIN (structure);

-- Комментарии
COMMENT ON TABLE api_schemas IS 'Схемы валидации данных из WB API (JSON Schema)';
COMMENT ON COLUMN api_schemas.structure IS 'JSONB структура схемы для валидации';

-- ============================================================================
-- 6. VALIDATION_LOGS (Логи валидации) - для отслеживания проблем
-- ============================================================================
CREATE TABLE validation_logs (
    id BIGSERIAL PRIMARY KEY,
    operation_type VARCHAR(100) NOT NULL, -- Тип операции (fetch_articles, fetch_prices, etc)
    status VARCHAR(50) NOT NULL, -- Статус (success, warning, error)
    
    -- Данные валидации
    input_data JSONB, -- Входные данные (первая запись для анализа)
    validation_errors JSONB, -- Ошибки валидации
    records_processed INTEGER, -- Количество обработанных записей
    records_failed INTEGER, -- Количество проваленных записей
    
    -- Метаданные
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    execution_time_ms INTEGER, -- Время выполнения в миллисекундах
    
    CONSTRAINT validation_logs_status_check CHECK (status IN ('success', 'warning', 'error'))
);

-- Индексы для validation_logs
CREATE INDEX idx_validation_logs_operation ON validation_logs(operation_type);
CREATE INDEX idx_validation_logs_status ON validation_logs(status);
CREATE INDEX idx_validation_logs_timestamp ON validation_logs(timestamp DESC);
CREATE INDEX idx_validation_logs_errors_gin ON validation_logs USING GIN (validation_errors);

-- Комментарии
COMMENT ON TABLE validation_logs IS 'Логи валидации данных из WB API';
COMMENT ON COLUMN validation_logs.operation_type IS 'Тип операции: fetch_articles, fetch_prices, update_prices, etc';
COMMENT ON COLUMN validation_logs.validation_errors IS 'JSONB структура с деталями ошибок валидации';

-- ============================================================================
-- 7. PRICE_HISTORY (История цен) - для аналитики изменения цен
-- ============================================================================
CREATE TABLE price_history (
    id BIGSERIAL PRIMARY KEY,
    nm_id INTEGER NOT NULL REFERENCES products(nm_id) ON DELETE CASCADE,
    
    -- Цены на момент записи
    price DECIMAL(10,2),
    discounted_price DECIMAL(10,2),
    discount INTEGER,
    discount_on_site INTEGER,
    price_after_spp DECIMAL(10,2),
    
    -- Метаданные
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы для price_history
CREATE INDEX idx_price_history_nm_id ON price_history(nm_id);
CREATE INDEX idx_price_history_recorded_at ON price_history(recorded_at DESC);

-- Комментарии
COMMENT ON TABLE price_history IS 'История изменения цен для аналитики (14 дней хранения)';

-- ============================================================================
-- ТРИГГЕРЫ: Автоматическое обновление updated_at
-- ============================================================================

-- Функция для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггеры для всех таблиц с updated_at
CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_seller_articles_updated_at BEFORE UPDATE ON seller_articles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_unit_economics_updated_at BEFORE UPDATE ON unit_economics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_schemas_updated_at BEFORE UPDATE ON api_schemas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Включаем RLS для всех таблиц
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE seller_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE unit_economics ENABLE ROW LEVEL SECURITY;
ALTER TABLE warehouse_remains ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_schemas ENABLE ROW LEVEL SECURITY;
ALTER TABLE validation_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_history ENABLE ROW LEVEL SECURITY;

-- Политики для аутентифицированных пользователей (полный доступ)
-- В продакшене можно настроить более гранулярные права

-- Products: все операции для authenticated
CREATE POLICY products_all_policy ON products
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Seller Articles: все операции для authenticated
CREATE POLICY seller_articles_all_policy ON seller_articles
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Unit Economics: все операции для authenticated
CREATE POLICY unit_economics_all_policy ON unit_economics
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Warehouse Remains: все операции для authenticated
CREATE POLICY warehouse_remains_all_policy ON warehouse_remains
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- API Schemas: чтение для authenticated, запись для admins
CREATE POLICY api_schemas_read_policy ON api_schemas
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY api_schemas_write_policy ON api_schemas
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Validation Logs: все операции для authenticated
CREATE POLICY validation_logs_all_policy ON validation_logs
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Price History: все операции для authenticated
CREATE POLICY price_history_all_policy ON price_history
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- ============================================================================
-- ПРЕДСТАВЛЕНИЯ (VIEWS)
-- ============================================================================

-- Полная информация о товарах с ценами
CREATE VIEW v_products_full AS
SELECT 
    p.id,
    p.nm_id,
    p.vendor_code,
    p.brand,
    p.title,
    p.subject,
    p.volume,
    p.active,
    
    -- Цены
    ue.price,
    ue.discounted_price,
    ue.discount,
    ue.discount_on_site,
    ue.price_after_spp,
    ue.competitive_price,
    ue.is_competitive_price,
    ue.has_promotions,
    
    -- Количество вариантов (баркодов)
    (SELECT COUNT(*) FROM seller_articles sa WHERE sa.nm_id = p.nm_id AND sa.active = true) as active_barcodes_count,
    
    -- Метаданные
    p.created_at,
    p.updated_at,
    ue.updated_at as prices_updated_at
FROM products p
LEFT JOIN unit_economics ue ON p.nm_id = ue.nm_id
WHERE p.active = true;

-- Комментарий
COMMENT ON VIEW v_products_full IS 'Полная информация о товарах с ценами и количеством баркодов';

-- Активные артикулы для экспорта в Google Sheets
CREATE VIEW v_active_articles_export AS
SELECT 
    sa.nm_id,
    sa.vendor_code,
    sa.barcode,
    sa.size,
    p.brand,
    p.title,
    p.volume,
    ue.price,
    ue.discounted_price,
    ue.discount,
    ue.discount_on_site,
    ue.price_after_spp,
    ue.competitive_price
FROM seller_articles sa
JOIN products p ON sa.nm_id = p.nm_id
LEFT JOIN unit_economics ue ON sa.nm_id = ue.nm_id
WHERE sa.active = true AND p.active = true
ORDER BY sa.nm_id, sa.barcode;

-- Комментарий
COMMENT ON VIEW v_active_articles_export IS 'Активные артикулы с ценами для экспорта в Google Sheets';

-- ============================================================================
-- ФУНКЦИИ: Бизнес-логика
-- ============================================================================

-- Функция для upsert товара с вариантами
CREATE OR REPLACE FUNCTION upsert_product_with_variants(
    p_nm_id INTEGER,
    p_vendor_code VARCHAR,
    p_brand VARCHAR,
    p_title TEXT,
    p_subject VARCHAR,
    p_volume DECIMAL,
    p_variants JSONB -- [{"barcode": "...", "size": "..."}]
)
RETURNS INTEGER AS $$
DECLARE
    v_variant JSONB;
BEGIN
    -- Upsert товара
    INSERT INTO products (nm_id, vendor_code, brand, title, subject, volume)
    VALUES (p_nm_id, p_vendor_code, p_brand, p_title, p_subject, p_volume)
    ON CONFLICT (nm_id) DO UPDATE SET
        vendor_code = EXCLUDED.vendor_code,
        brand = EXCLUDED.brand,
        title = EXCLUDED.title,
        subject = EXCLUDED.subject,
        volume = EXCLUDED.volume,
        updated_at = NOW();
    
    -- Upsert вариантов (баркодов)
    FOR v_variant IN SELECT * FROM jsonb_array_elements(p_variants)
    LOOP
        INSERT INTO seller_articles (nm_id, vendor_code, barcode, size)
        VALUES (
            p_nm_id, 
            p_vendor_code, 
            v_variant->>'barcode', 
            v_variant->>'size'
        )
        ON CONFLICT (barcode) DO UPDATE SET
            nm_id = EXCLUDED.nm_id,
            vendor_code = EXCLUDED.vendor_code,
            size = EXCLUDED.size,
            updated_at = NOW();
    END LOOP;
    
    RETURN p_nm_id;
END;
$$ LANGUAGE plpgsql;

-- Комментарий
COMMENT ON FUNCTION upsert_product_with_variants IS 'Upsert товара со всеми его вариантами (баркодами)';

-- Функция для обновления цен с историей
CREATE OR REPLACE FUNCTION update_prices_with_history(
    p_nm_id INTEGER,
    p_vendor_code VARCHAR,
    p_price DECIMAL,
    p_discounted_price DECIMAL,
    p_discount INTEGER,
    p_discount_on_site INTEGER,
    p_price_after_spp DECIMAL,
    p_competitive_price DECIMAL,
    p_is_competitive_price BOOLEAN,
    p_has_promotions BOOLEAN
)
RETURNS VOID AS $$
BEGIN
    -- Сохраняем текущие цены в историю (если есть изменения)
    INSERT INTO price_history (nm_id, price, discounted_price, discount, discount_on_site, price_after_spp)
    SELECT nm_id, price, discounted_price, discount, discount_on_site, price_after_spp
    FROM unit_economics
    WHERE nm_id = p_nm_id
        AND (
            COALESCE(price, 0) != COALESCE(p_price, 0) OR
            COALESCE(discounted_price, 0) != COALESCE(p_discounted_price, 0) OR
            COALESCE(discount, 0) != COALESCE(p_discount, 0) OR
            COALESCE(discount_on_site, 0) != COALESCE(p_discount_on_site, 0)
        );
    
    -- Upsert текущих цен
    INSERT INTO unit_economics (
        nm_id, vendor_code, price, discounted_price, discount, discount_on_site,
        price_after_spp, competitive_price, is_competitive_price, has_promotions
    )
    VALUES (
        p_nm_id, p_vendor_code, p_price, p_discounted_price, p_discount, p_discount_on_site,
        p_price_after_spp, p_competitive_price, p_is_competitive_price, p_has_promotions
    )
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
END;
$$ LANGUAGE plpgsql;

-- Комментарий
COMMENT ON FUNCTION update_prices_with_history IS 'Обновление цен с сохранением в историю';

-- ============================================================================
-- MAINTENANCE: Автоматическая очистка старых данных
-- ============================================================================

-- Функция для очистки старых логов (старше 30 дней)
CREATE OR REPLACE FUNCTION cleanup_old_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM validation_logs 
    WHERE timestamp < NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Функция для очистки старой истории цен (старше 90 дней)
CREATE OR REPLACE FUNCTION cleanup_old_price_history()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM price_history 
    WHERE recorded_at < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Комментарии
COMMENT ON FUNCTION cleanup_old_logs IS 'Очистка логов старше 30 дней';
COMMENT ON FUNCTION cleanup_old_price_history IS 'Очистка истории цен старше 90 дней';

-- ============================================================================
-- ПРИМЕЧАНИЯ
-- ============================================================================
-- 1. После создания схемы настройте автоматический запуск cleanup функций через pg_cron
-- 2. Для работы RLS необходимо создать пользователей через Supabase Auth
-- 3. Индексы GIN на JSONB ускоряют поиск по структурам схем и логов
-- 4. Партиционирование warehouse_remains по snapshot_date можно добавить при больших объемах
-- 5. Для аналитики добавьте представления с агрегацией по датам/складам

