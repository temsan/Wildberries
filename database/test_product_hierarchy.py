#!/usr/bin/env python3
"""
Тест иерархии продуктов: nmID → vendorCode → barcodes
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.integrations.discounts_prices_enhanced import DiscountsPricesDBProcessor


def test_product_hierarchy():
    """Тестирует иерархию продуктов"""
    print("🧪 ТЕСТ ИЕРАРХИИ ПРОДУКТОВ")
    print("=" * 50)
    print("Структура: nmID → vendorCode → barcodes")
    print("=" * 50)
    
    # Инициализация
    processor = DiscountsPricesDBProcessor()
    
    # Проверка подключения к БД
    connections = processor.test_connections()
    if not connections['database']:
        print("❌ Нет подключения к БД")
        return
    
    print("✅ Подключение к БД установлено")
    
    # Получаем обзор иерархии
    print("\n📊 Получаем обзор иерархии...")
    overview = processor.get_products_overview()
    
    if 'error' in overview:
        print(f"❌ Ошибка: {overview['error']}")
        return
    
    # Показываем общую статистику
    hierarchy = overview['hierarchy_summary']
    print(f"\n📈 ОБЩАЯ СТАТИСТИКА:")
    print(f"   • Продукты (nmID): {hierarchy['products'].get('total_products', 0)}")
    print(f"   • Активные продукты: {hierarchy['products'].get('active_products', 0)}")
    print(f"   • Артикулы продавца: {hierarchy['vendor_codes'].get('unique_vendor_codes', 0)}")
    print(f"   • Всего баркодов: {hierarchy['barcodes'].get('total_barcodes', 0)}")
    print(f"   • Активных баркодов: {hierarchy['barcodes'].get('active_barcodes', 0)}")
    print(f"   • Уникальных баркодов: {hierarchy['barcodes'].get('unique_barcodes', 0)}")
    print(f"   • Уникальных брендов: {hierarchy['products'].get('unique_brands', 0)}")
    
    # Показываем примеры товаров с баркодами
    if overview['products_with_barcodes']:
        print(f"\n📦 ТОВАРЫ С БАРКОДАМИ (топ 10):")
        print("-" * 60)
        for i, item in enumerate(overview['products_with_barcodes'][:10], 1):
            print(f"{i:2d}. nmID: {item['nm_id']}")
            print(f"    Артикул: {item['vendor_code']}")
            print(f"    Бренд: {item['brand']}")
            print(f"    Название: {item['title'][:50]}...")
            print(f"    Баркодов: {item['barcodes_count']} (активных: {item['active_barcodes_count']})")
            print()
    
    # Показываем топ брендов
    if overview['top_brands']:
        print(f"🏷️  ТОП БРЕНДОВ:")
        print("-" * 40)
        for i, brand in enumerate(overview['top_brands'][:10], 1):
            print(f"{i:2d}. {brand['brand']}")
            print(f"    Продуктов: {brand['products_count']}")
            print(f"    Артикулов: {brand['vendor_codes_count']}")
            print(f"    Баркодов: {brand['barcodes_count']}")
            print()
    
    # Получаем детальную информацию о конкретном товаре
    if overview['products_with_barcodes']:
        sample_nm_id = overview['products_with_barcodes'][0]['nm_id']
        print(f"🔍 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О ТОВАРЕ {sample_nm_id}:")
        print("-" * 50)
        
        try:
            # Получаем детали товара с баркодами
            detail_query = f"""
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
            WHERE p.nm_id = {sample_nm_id}
            ORDER BY sa.barcode
            """
            
            detail_result = processor.db_client.client.rpc('exec_sql', {'sql': detail_query}).execute()
            
            if detail_result.data:
                product_info = detail_result.data[0]
                print(f"📦 Продукт:")
                print(f"   • nmID: {product_info['nm_id']}")
                print(f"   • Артикул продавца: {product_info['vendor_code']}")
                print(f"   • Бренд: {product_info['brand']}")
                print(f"   • Название: {product_info['title']}")
                print(f"   • Категория: {product_info['subject']}")
                print(f"   • Объем: {product_info['volume']} л")
                print(f"   • Цена: {product_info['price']} ₽")
                print(f"   • Цена со скидкой: {product_info['discounted_price']} ₽")
                print(f"   • Скидка: {product_info['discount']}%")
                
                print(f"\n🏷️  Баркоды ({len(detail_result.data)}):")
                for barcode_info in detail_result.data:
                    status = "✅" if barcode_info['barcode_active'] else "❌"
                    print(f"   {status} {barcode_info['barcode']} (размер: {barcode_info['size'] or 'не указан'})")
        
        except Exception as e:
            print(f"❌ Ошибка получения деталей: {e}")
    
    print(f"\n✅ Тест иерархии завершен!")


if __name__ == "__main__":
    test_product_hierarchy()
