#!/usr/bin/env python3
"""
Скрипт для запуска синхронизации Discounts-Prices с БД.
Заменяет Google Sheets интеграцию.
"""

import sys
import argparse
from pathlib import Path

# Добавляем корневую директорию в path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.integrations.discounts_prices_enhanced import DiscountsPricesDBProcessor


def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description='Синхронизация Discounts-Prices с БД')
    
    parser.add_argument(
        '--max-goods', 
        type=int, 
        default=None,
        help='Максимальное количество товаров для обработки'
    )
    
    parser.add_argument(
        '--batch-size', 
        type=int, 
        default=50,
        help='Размер батча для обработки (по умолчанию: 50)'
    )
    
    parser.add_argument(
        '--sleep', 
        type=float, 
        default=1.0,
        help='Задержка между запросами в секундах (по умолчанию: 1.0)'
    )
    
    parser.add_argument(
        '--export', 
        type=str, 
        default=None,
        help='Путь для экспорта данных в JSON'
    )
    
    parser.add_argument(
        '--analytics', 
        action='store_true',
        help='Показать аналитику после синхронизации'
    )
    
    parser.add_argument(
        '--test-only', 
        action='store_true',
        help='Только тест подключений без синхронизации'
    )
    
    args = parser.parse_args()
    
    print("🚀 СИНХРОНИЗАЦИЯ DISCOUNTS-PRICES С БД")
    print("=" * 50)
    print(f"Максимум товаров: {args.max_goods or 'без ограничений'}")
    print(f"Размер батча: {args.batch_size}")
    print(f"Задержка: {args.sleep}с")
    print("=" * 50)
    
    # Инициализация процессора
    processor = DiscountsPricesDBProcessor()
    
    # Проверка подключений
    print("🔍 Проверяем подключения...")
    connections = processor.test_connections()
    
    if not connections['database']:
        print("❌ Нет подключения к БД")
        print("💡 Проверьте настройки в api_keys.py")
        return 1
    
    if not connections['api']:
        print("❌ Нет подключения к Discounts-Prices API")
        print("💡 Проверьте токены в api_keys.py")
        return 1
    
    print("✅ Все подключения работают")
    
    if args.test_only:
        print("🧪 Тест подключений завершен успешно")
        return 0
    
    try:
        # Синхронизация
        print("\n🚀 Запускаем синхронизацию...")
        stats = processor.sync_prices_to_db(
            max_goods=args.max_goods,
            batch_size=args.batch_size,
            sleep_seconds=args.sleep
        )
        
        print(f"\n📊 Результат синхронизации:")
        print(f"   • Всего товаров: {stats['total']}")
        print(f"   • Успешно: {stats['success']}")
        print(f"   • Ошибок: {stats['failed']}")
        print(f"   • Время: {stats['execution_time_ms']/1000:.2f}с")
        
        # Аналитика
        if args.analytics:
            print("\n📈 Получаем аналитику...")
            analytics = processor.get_price_analytics(days=7)
            
            if 'error' not in analytics:
                stats_data = analytics['statistics']
                print(f"📊 Аналитика за 7 дней:")
                print(f"   • Всего товаров: {stats_data.get('total_products', 0)}")
                print(f"   • Средняя цена: {stats_data.get('avg_price', 0):.2f} ₽")
                print(f"   • Товаров со скидками: {stats_data.get('products_with_discount', 0)}")
                print(f"   • Средняя скидка: {stats_data.get('avg_discount', 0):.1f}%")
                print(f"   • Изменений цен: {len(analytics['price_changes'])}")
            else:
                print(f"❌ Ошибка получения аналитики: {analytics['error']}")
        
        # Экспорт
        if args.export:
            print(f"\n📤 Экспортируем данные в {args.export}...")
            export_success = processor.export_to_json(args.export, args.max_goods)
            
            if export_success:
                print("✅ Экспорт успешен")
            else:
                print("❌ Экспорт не удался")
        
        print("\n🎉 Синхронизация завершена успешно!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Ошибка синхронизации: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
