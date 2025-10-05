#!/usr/bin/env python3
"""
Анализ структуры таблицы на основе URL
Помогает понять, как организовать хранение данных
"""

def analyze_table_structure():
    """Анализирует структуру таблицы"""
    print("АНАЛИЗ СТРУКТУРЫ ТАБЛИЦЫ")
    print("=" * 60)
    print("URL: https://docs.google.com/spreadsheets/d/1Aufum97SY2fChBKNyzP0tslUYbCQ6cCd41EkoEo05SM/edit")
    print("=" * 60)
    
    # На основе описания таблицы
    # Предполагаемая структура таблицы
    print("\nПРЕДПОЛАГАЕМАЯ СТРУКТУРА ТАБЛИЦЫ:")
    print("-" * 40)
    
    # Заголовки таблицы (на основе описания)
    headers = [
        "Продукт",           # A
        "Баркод",           # B  
        "Конверсии",        # C
        "Рекламные компании", # D
        "Заказы",           # E
        "Продажи",          # F
        "Еженедельный отчет", # G
        "Остатки",          # H
        "Себестоимость"     # I
    ]
    
    print("Заголовки таблицы:")
    for i, header in enumerate(headers, 1):
        print(f"   {i:2d}. {header}")
    
    # Детализация по столбцам
    print(f"\nДЕТАЛИЗАЦИЯ ПО СТОЛБЦАМ:")
    print("-" * 30)
    
    product_details = [
        "Артикул",
        "Артикул продавца", 
        "Баркод",
        "Название",
        "Категория WB"
    ]
    
    barcode_details = [
        "Артикул",
        "Баркод", 
        "Размер"
    ]
    
    print(f"Столбец A - Продукт:")
    for detail in product_details:
        print(f"   • {detail}")
    
    print(f"\nСтолбец B - Баркод:")
    for detail in barcode_details:
        print(f"   • {detail}")
    
    # Анализ по типу хранения
    print(f"\nАНАЛИЗ ПО ТИПУ ХРАНЕНИЯ:")
    print("-" * 40)
    
    # Временные ряды (нужна история)
    time_series = [
        "Конверсии",
        "Рекламные компании", 
        "Заказы",
        "Продажи",
        "Еженедельный отчет",
        "Остатки",
        "Себестоимость"
    ]
    
    # Простое обновление (текущее состояние)
    simple_update = [
        "Продукт",
        "Артикул",
        "Артикул продавца",
        "Баркод", 
        "Размер",
        "Название",
        "Категория WB",
        "Бренд"
    ]
    
    print(f"ВРЕМЕННЫЕ РЯДЫ (нужна история изменений):")
    for item in time_series:
        print(f"   • {item}")
    
    print(f"\nПРОСТОЕ ОБНОВЛЕНИЕ (текущее состояние):")
    for item in simple_update:
        print(f"   • {item}")
    
    # Рекомендации по структуре БД
    print(f"\nРЕКОМЕНДАЦИИ ПО СТРУКТУРЕ БД:")
    print("-" * 50)
    
    print("Предлагаемая структура:")
    print()
    print("1. PRODUCTS (основная таблица артикулов):")
    print("   CREATE TABLE products (")
    print("       id BIGSERIAL PRIMARY KEY,")
    print("       nm_id INTEGER NOT NULL UNIQUE,           -- Артикул WB")
    print("       vendor_code VARCHAR(255) NOT NULL,       -- Артикул продавца")
    print("       brand VARCHAR(255),                      -- Бренд")
    print("       title TEXT,                              -- Название")
    print("       subject VARCHAR(255),                    -- Категория WB")
    print("       volume DECIMAL(10,3),                    -- Объем упаковки")
    print("       active BOOLEAN DEFAULT true,             -- Активность")
    print("       created_at TIMESTAMP DEFAULT NOW(),")
    print("       updated_at TIMESTAMP DEFAULT NOW()")
    print("   );")
    print()
    
    print("2. SELLER_ARTICLES (размеры/баркоды):")
    print("   CREATE TABLE seller_articles (")
    print("       id BIGSERIAL PRIMARY KEY,")
    print("       nm_id INTEGER REFERENCES products(nm_id), -- Связь с артикулом")
    print("       barcode VARCHAR(255) NOT NULL UNIQUE,     -- Штрихкод")
    print("       size VARCHAR(100),                        -- Размер")
    print("       active BOOLEAN DEFAULT true,              -- Активность")
    print("       created_at TIMESTAMP DEFAULT NOW(),")
    print("       updated_at TIMESTAMP DEFAULT NOW()")
    print("   );")
    print()
    
    print("3. METRICS_HISTORY (временные ряды):")
    print("   CREATE TABLE metrics_history (")
    print("       id BIGSERIAL PRIMARY KEY,")
    print("       nm_id INTEGER REFERENCES products(nm_id), -- Связь с артикулом")
    print("       recorded_at TIMESTAMP DEFAULT NOW(),      -- Время записи")
    print("       conversions DECIMAL(10,2),                -- Конверсии")
    print("       orders INTEGER,                           -- Заказы")
    print("       sales DECIMAL(10,2),                      -- Продажи")
    print("       stock_quantity INTEGER,                   -- Остатки")
    print("       cost_price DECIMAL(10,2),                 -- Себестоимость")
    print("       ad_spend DECIMAL(10,2),                   -- Рекламные траты")
    print("       ad_campaigns JSONB                        -- Рекламные компании")
    print("   );")
    print()
    
    print("4. WEEKLY_REPORTS (еженедельные отчеты):")
    print("   CREATE TABLE weekly_reports (")
    print("       id BIGSERIAL PRIMARY KEY,")
    print("       nm_id INTEGER REFERENCES products(nm_id), -- Связь с артикулом")
    print("       week_start DATE,                          -- Начало недели")
    print("       week_end DATE,                            -- Конец недели")
    print("       report_data JSONB,                        -- Данные отчета")
    print("       created_at TIMESTAMP DEFAULT NOW()")
    print("   );")
    
    # Логика обработки
    print(f"\nЛОГИКА ОБРАБОТКИ ДАННЫХ:")
    print("-" * 40)
    
    print("1. Артикулы (PRODUCTS):")
    print("   • Создание/обновление при получении из API")
    print("   • Управление по nmID")
    print("   • Баркоды = размеры (M, L, XL)")
    print()
    
    print("2. Метрики (METRICS_HISTORY):")
    print("   • Запись при каждом обновлении")
    print("   • Хранение истории изменений")
    print("   • Анализ трендов и динамики")
    print()
    
    print("3. Отчеты (WEEKLY_REPORTS):")
    print("   • Агрегация данных за неделю")
    print("   • JSONB для гибкости структуры")
    print("   • Связь с артикулом")
    
    # Итоговые рекомендации
    print(f"\nИТОГОВЫЕ РЕКОМЕНДАЦИИ:")
    print("-" * 40)
    print("1. Иерархия: nmID -> vendorCode -> barcodes")
    print("2. Временные ряды: конверсии, заказы, продажи, остатки")
    print("3. Простое обновление: артикул, бренд, название, размеры")
    print("4. Аналитика: история изменений ключевых метрик")
    print("5. Управление: по артикулу (nmID) целиком")


if __name__ == "__main__":
    analyze_table_structure()
