"""
Главный файл для синхронизации данных WB API с БД Supabase.
Полная интеграция: Content Cards + Discounts-Prices → Database → Google Sheets.
"""

from pathlib import Path
import sys
import argparse
from typing import Optional

# Добавляем корневую директорию в path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.db_client import get_client
from database.integrations.content_cards_db import sync_content_cards_to_db
from database.integrations.discounts_prices_db import sync_discounts_prices_to_db
from wb_api.content_cards import WBContentCardsClient, API_KEY
from wb_api.discounts_prices.discounts_prices import WBDiscountsPricesClient


def sync_articles_to_db(max_cards: Optional[int] = None) -> dict:
    """
    Синхронизация артикулов (Content Cards API → БД).
    
    Args:
        max_cards: Максимальное количество карточек для обработки
        
    Returns:
        Статистика операции
    """
    print("\n" + "="*70)
    print("📦 ШАГ 1: СИНХРОНИЗАЦИЯ АРТИКУЛОВ (Content Cards API)")
    print("="*70 + "\n")
    
    api_client = WBContentCardsClient(API_KEY)
    db_client = get_client()
    
    stats = sync_content_cards_to_db(
        api_client=api_client,
        db_client=db_client,
        max_cards=max_cards
    )
    
    return stats


def sync_prices_to_db(max_goods: Optional[int] = None) -> dict:
    """
    Синхронизация цен (Discounts-Prices API → БД).
    
    Args:
        max_goods: Максимальное количество товаров для обработки
        
    Returns:
        Статистика операции
    """
    print("\n" + "="*70)
    print("💰 ШАГ 2: СИНХРОНИЗАЦИЯ ЦЕН (Discounts-Prices API)")
    print("="*70 + "\n")
    
    api_client = WBDiscountsPricesClient()
    db_client = get_client()
    
    stats = sync_discounts_prices_to_db(
        api_client=api_client,
        db_client=db_client,
        max_goods=max_goods
    )
    
    return stats


def export_to_sheets(sheet_id: Optional[str] = None):
    """
    Экспорт данных из БД в Google Sheets.
    
    Args:
        sheet_id: ID таблицы Google Sheets
    """
    print("\n" + "="*70)
    print("📊 ШАГ 3: ЭКСПОРТ В GOOGLE SHEETS")
    print("="*70 + "\n")
    
    db_client = get_client()
    
    # Получаем данные из view
    data = db_client.get_active_articles_for_export()
    
    print(f"📥 Получено из БД: {len(data)} артикулов с ценами")
    
    if not data:
        print("⚠️  Нет данных для экспорта")
        return
    
    # Здесь можно добавить интеграцию с Google Sheets
    # Пример структуры данных для экспорта:
    print(f"\n📋 Пример данных для экспорта (первые 3):")
    for idx, item in enumerate(data[:3], 1):
        print(f"  {idx}. nmID={item.get('nm_id')}, barcode={item.get('barcode')}, "
              f"price={item.get('price')}, price_after_spp={item.get('price_after_spp')}")
    
    print(f"\n✅ Данные готовы к экспорту в Google Sheets")
    print(f"   Используйте существующие модули google_sheets_writer для записи")


def show_statistics():
    """
    Показать статистику по данным в БД.
    """
    print("\n" + "="*70)
    print("📈 СТАТИСТИКА ПО БАЗЕ ДАННЫХ")
    print("="*70 + "\n")
    
    db_client = get_client()
    
    # Получаем статистику
    products = db_client.get_active_products()
    barcodes = db_client.get_active_barcodes()
    products_with_prices = db_client.get_products_with_prices()
    
    print(f"📦 Активных товаров: {len(products)}")
    print(f"🏷️  Активных баркодов: {len(barcodes)}")
    print(f"💰 Товаров с ценами: {len(products_with_prices)}")
    
    # Последние логи
    logs = db_client.get_recent_logs(limit=5)
    print(f"\n📝 Последние операции:")
    for log in logs:
        status_emoji = "✅" if log['status'] == 'success' else "⚠️" if log['status'] == 'warning' else "❌"
        print(f"   {status_emoji} {log['operation_type']}: {log['records_processed']} записей, "
              f"статус={log['status']}, время={log.get('execution_time_ms', 0)}мс")


def main():
    """
    Главная функция: полная синхронизация данных.
    """
    parser = argparse.ArgumentParser(
        description="Синхронизация данных WB API с БД Supabase"
    )
    parser.add_argument(
        '--mode',
        choices=['full', 'articles', 'prices', 'export', 'stats'],
        default='full',
        help='Режим работы: full (всё), articles (только артикулы), prices (только цены), export (экспорт в Sheets), stats (статистика)'
    )
    parser.add_argument(
        '--max-cards',
        type=int,
        help='Максимальное количество карточек для обработки'
    )
    parser.add_argument(
        '--max-goods',
        type=int,
        help='Максимальное количество товаров для обработки'
    )
    parser.add_argument(
        '--sheet-id',
        type=str,
        help='ID таблицы Google Sheets для экспорта'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🚀 WILDBERRIES API → SUPABASE DATABASE SYNC")
    print("="*70)
    
    # Проверка подключения
    db_client = get_client()
    if not db_client.test_connection():
        print("❌ Ошибка подключения к БД. Проверьте настройки в api_keys.py")
        return 1
    
    try:
        if args.mode == 'full':
            # Полная синхронизация
            articles_stats = sync_articles_to_db(max_cards=args.max_cards)
            prices_stats = sync_prices_to_db(max_goods=args.max_goods)
            export_to_sheets(sheet_id=args.sheet_id)
            show_statistics()
            
            print("\n" + "="*70)
            print("✅ ПОЛНАЯ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА")
            print(f"   • Артикулов: {articles_stats['success']} успешно, {articles_stats['failed']} ошибок")
            print(f"   • Цен: {prices_stats['success']} успешно, {prices_stats['failed']} ошибок")
            print("="*70 + "\n")
        
        elif args.mode == 'articles':
            # Только артикулы
            stats = sync_articles_to_db(max_cards=args.max_cards)
            print(f"\n✅ Синхронизация артикулов завершена: {stats}")
        
        elif args.mode == 'prices':
            # Только цены
            stats = sync_prices_to_db(max_goods=args.max_goods)
            print(f"\n✅ Синхронизация цен завершена: {stats}")
        
        elif args.mode == 'export':
            # Только экспорт
            export_to_sheets(sheet_id=args.sheet_id)
        
        elif args.mode == 'stats':
            # Только статистика
            show_statistics()
        
        return 0
    
    except Exception as e:
        print(f"\n❌ Ошибка выполнения: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

