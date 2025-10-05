-- ============================================================================
-- МИГРАЦИЯ 001: Исправление проблем безопасности
-- ============================================================================
-- Дата: 2025-01-04
-- Описание: Исправляет предупреждения линтера Supabase
-- - Добавляет SET search_path в функции
-- - Объединяет множественные RLS политики
-- - Пересоздает views без SECURITY DEFINER
-- ============================================================================

-- ============================================================================
-- 1. ИСПРАВЛЕНИЕ ФУНКЦИЙ - добавление SET search_path
-- ============================================================================

-- Функция update_updated_at_column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER 
SET search_path = public
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Функция upsert_product_with_variants
CREATE OR REPLACE FUNCTION upsert_product_with_variants(
    p_nm_id INTEGER,
    p_vendor_code VARCHAR,
    p_brand VARCHAR,
    p_title TEXT,
    p_subject VARCHAR,
    p_volume DECIMAL,
    p_variants JSONB
)
RETURNS INTEGER 
SET search_path = public
AS $$
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
    
    -- Удаляем старые варианты
    DELETE FROM seller_articles WHERE nm_id = p_nm_id;
    
    -- Добавляем новые варианты
    FOR v_variant IN SELECT * FROM jsonb_array_elements(p_variants)
    LOOP
        INSERT INTO seller_articles (nm_id, vendor_code, barcode, size)
        VALUES (
            p_nm_id,
            p_vendor_code,
            v_variant->>'barcode',
            v_variant->>'size'
        )
        ON CONFLICT (nm_id, barcode) DO UPDATE SET
            vendor_code = EXCLUDED.vendor_code,
            size = EXCLUDED.size,
            updated_at = NOW();
    END LOOP;
    
    RETURN p_nm_id;
END;
$$ LANGUAGE plpgsql;

-- Функция update_prices_with_history
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
RETURNS VOID 
SET search_path = public
AS $$
BEGIN
    -- Сохраняем текущие цены в историю (если есть изменения)
    INSERT INTO price_history (nm_id, price, discounted_price, discount, discount_on_site, price_after_spp)
    SELECT nm_id, price, discounted_price, discount, discount_on_site, price_after_spp
    FROM unit_economics
    WHERE nm_id = p_nm_id
    AND (
        price != p_price OR 
        discounted_price != p_discounted_price OR 
        discount != p_discount OR
        discount_on_site != p_discount_on_site OR
        price_after_spp != p_price_after_spp
    );
    
    -- Обновляем цены
    INSERT INTO unit_economics (
        nm_id, vendor_code, price, discounted_price, discount, 
        discount_on_site, price_after_spp, competitive_price, 
        is_competitive_price, has_promotions
    )
    VALUES (
        p_nm_id, p_vendor_code, p_price, p_discounted_price, p_discount,
        p_discount_on_site, p_price_after_spp, p_competitive_price,
        p_is_competitive_price, p_has_promotions
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

-- Функция cleanup_old_logs
CREATE OR REPLACE FUNCTION cleanup_old_logs()
RETURNS INTEGER 
SET search_path = public
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM validation_logs 
    WHERE timestamp < NOW() - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Функция cleanup_old_price_history
CREATE OR REPLACE FUNCTION cleanup_old_price_history()
RETURNS INTEGER 
SET search_path = public
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM price_history 
    WHERE recorded_at < NOW() - INTERVAL '90 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 2. ИСПРАВЛЕНИЕ RLS ПОЛИТИК - объединение множественных политик
-- ============================================================================

-- Удаляем старые политики api_schemas
DROP POLICY IF EXISTS api_schemas_read_policy ON api_schemas;
DROP POLICY IF EXISTS api_schemas_write_policy ON api_schemas;

-- Создаем единую политику для api_schemas
CREATE POLICY api_schemas_policy ON api_schemas
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- ============================================================================
-- 3. ПЕРЕСОЗДАНИЕ VIEWS - убираем SECURITY DEFINER
-- ============================================================================

-- Удаляем старые views
DROP VIEW IF EXISTS v_products_full CASCADE;
DROP VIEW IF EXISTS v_active_articles_export CASCADE;

-- Создаем v_products_full без SECURITY DEFINER
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

-- Создаем v_active_articles_export без SECURITY DEFINER
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
    ue.is_competitive_price,
    ue.has_promotions,
    sa.active,
    sa.created_at,
    sa.updated_at
FROM seller_articles sa
JOIN products p ON sa.nm_id = p.nm_id
LEFT JOIN unit_economics ue ON sa.nm_id = ue.nm_id
WHERE sa.active = true AND p.active = true;

-- ============================================================================
-- КОММЕНТАРИИ
-- ============================================================================

COMMENT ON FUNCTION update_updated_at_column() IS 'Обновляет updated_at при изменении записи (исправлено: добавлен SET search_path)';
COMMENT ON FUNCTION upsert_product_with_variants IS 'Upsert товара со всеми его вариантами (исправлено: добавлен SET search_path)';
COMMENT ON FUNCTION update_prices_with_history IS 'Обновляет цены с сохранением истории (исправлено: добавлен SET search_path)';
COMMENT ON FUNCTION cleanup_old_logs() IS 'Очищает старые логи (исправлено: добавлен SET search_path)';
COMMENT ON FUNCTION cleanup_old_price_history() IS 'Очищает старую историю цен (исправлено: добавлен SET search_path)';

COMMENT ON VIEW v_products_full IS 'Полная информация о товарах с ценами (исправлено: убран SECURITY DEFINER)';
COMMENT ON VIEW v_active_articles_export IS 'Активные артикулы для экспорта (исправлено: убран SECURITY DEFINER)';

-- ============================================================================
-- ЗАВЕРШЕНИЕ МИГРАЦИИ
-- ============================================================================

-- Записываем информацию о миграции
INSERT INTO validation_logs (operation_type, status, input_data)
VALUES (
    'migration_001_fix_security', 
    'success', 
    '{"migration": "001_fix_security_issues", "date": "2025-01-04", "description": "Исправление проблем безопасности выполнено успешно"}'
);
