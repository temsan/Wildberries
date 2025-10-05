#!/usr/bin/env python3
"""
Тест конфигурации хранения артикулов
Демонстрирует правильную иерархию: nmID → vendorCode → barcodes
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.integrations.discounts_prices_enhanced import DiscountsPricesDBProcessor


def test_articles_hierarchy():
    """Тестирует иерархию артикулов"""
    print("🧪 ТЕСТ КОНФИГУРАЦИИ АРТИКУЛОВ")
    print("=" * 60)
    print("Иерархия: nmID → vendorCode → barcodes (размеры)")
    print("Тип хранения: ПРОСТОЕ ОБНОВЛЕНИЕ (без истории)")
    print("=" * 60)
    
    # Инициализация
    processor = DiscountsPricesDBProcessor()
    
    # Проверка подключения к БД
    connections = processor.test_connections()
    if not connections['database']:
        print("❌ Нет подключения к БД")
        return
    
    print("✅ Подключение к БД установлено")
    
    # Тестовые данные для демонстрации
    test_items = [
        {
            'nmID': 12345,
            'vendorCode': 'NIK-001',
            'brand': 'Nike',
            'title': 'Футболка Nike Sport',
            'subject': 'Одежда',
            'volume': 0.1,
            'barcodes': ['1234567890123', '1234567890124', '1234567890125'],
            'size': 'M'
        },
        {
            'nmID': 67890,
            'vendorCode': 'AD-002',
            'brand': 'Adidas',
            'title': 'Кроссовки Adidas Ultra',
            'subject': 'Обувь',
            'volume': 0.5,
            'barcodes': ['9876543210987', '9876543210988'],
            'size': '42'
        }
    ]
    
    print(f"\n📦 Обрабатываем {len(test_items)} тестовых товара...")
    
    for i, item in enumerate(test_items, 1):
        print(f"\n{i}. Обработка товара nmID={item['nmID']}")
        
        # Обрабатываем данные товара
        processed = processor.process_price_data(item)
        
        print(f"   • Артикул: {processed['nm_id']}")
        print(f"   • Артикул продавца: {processed['vendor_code']}")
        print(f"   • Бренд: {processed['brand']}")
        print(f"   • Название: {processed['title'][:50]}...")
        print(f"   • Размеров: {len(processed['variants'])}")
        
        for variant in processed['variants']:
            print(f"     - Баркод: {variant['barcode']} (размер: {variant['size']})")
    
    # Демонстрация запросов
    print(f"\n📊 Демонстрация запросов к БД...")
    
    try:
        # 1. Статистика артикулов
        stats_query = """
        SELECT 
            COUNT(*) as total_products,
            COUNT(DISTINCT nm_id) as unique_articles,
            AVG(volume) as avg_volume
        FROM products
        WHERE active = true
        """
        
        stats_result = processor.db_client.client.rpc('exec_sql', {'sql': stats_query}).execute()
        if stats_result.data:
            stats = stats_result.data[0]
            print(f"   📈 Статистика артикулов:")
            print(f"      • Всего товаров: {stats.get('total_products', 0)}")
            print(f"      • Уникальных артикулов: {stats.get('unique_articles', 0)}")
            print(f"      • Средний объем: {stats.get('avg_volume', 0):.2f} л")
        
        # 2. Топ артикулов по размерам
        top_query = """
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
        LIMIT 5
        """
        
        top_result = processor.db_client.client.rpc('exec_sql', {'sql': top_query}).execute()
        if top_result.data:
            print(f"\n   🏆 Топ артикулов по количеству размеров:")
            for i, item in enumerate(top_result.data[:3], 1):
                print(f"      {i}. nmID {item['nm_id']} ({item['vendor_code']}): {item['sizes_count']} размеров")
                print(f"         Бренд: {item['brand']}")
                print(f"         Название: {item['title'][:40]}...")
    
    except Exception as e:
        print(f"   ⚠️  Ошибка выполнения запросов: {e}")
    
    print(f"\n✅ Тест конфигурации завершен!")
    print(f"\n💡 Основные принципы:")
    print(f"   • Управление по артикулу (nmID)")
    print(f"   • Баркод = размер товара (M, L, XL)")
    print(f"   • Цены общие для всех размеров")
    print(f"   • Простое обновление (без истории)")
    print(f"   • Закупки по артикулу целиком")


if __name__ == "__main__":
    test_articles_hierarchy()
