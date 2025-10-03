"""
Интеграция Discounts-Prices API с базой данных.
Upsert цен и скидок из WBDiscountsPricesClient.
"""

from typing import List, Dict, Any
import time
from pathlib import Path
import sys

# Добавляем корневую директорию в path для импорта
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from database.db_client import get_client


def process_price_list(prices: List[Any], field_name: str, nm_id: int) -> float:
    """
    Обрабатывает список цен (prices или discountedPrices).
    Логика из data_processor.py
    
    Args:
        prices: Список цен
        field_name: Название поля для логирования
        nm_id: ID товара
        
    Returns:
        Обработанная цена
    """
    if not prices:
        return 0.0
    
    if len(prices) == 1:
        return float(prices[0])
    
    # Проверяем, одинаковые ли все цены
    unique_prices = set(prices)
    
    if len(unique_prices) == 1:
        return float(prices[0])
    else:
        # Цены разные - берем максимальную
        max_price = max(prices)
        print(f"⚠️  nmID {nm_id}: В {field_name} разные цены, используем max={max_price}")
        return float(max_price)


def calculate_price_after_spp(discounted_price: float, discount_on_site: float) -> float:
    """
    Рассчитывает цену после СПП.
    
    Args:
        discounted_price: Цена со скидкой
        discount_on_site: СПП (%)
        
    Returns:
        Цена после СПП
    """
    if not discount_on_site or discount_on_site <= 0:
        return discounted_price
    
    price_after_spp = discounted_price * (1 - discount_on_site / 100)
    return round(price_after_spp, 2)


def process_single_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обрабатывает один товар из API.
    Адаптация из data_processor.py
    
    Args:
        item: Товар из Discounts-Prices API
        
    Returns:
        Обработанный товар
    """
    nm_id = item.get('nmID', 0)
    vendor_code = item.get('vendorCode', '')
    
    # Обработка цен
    prices = process_price_list(item.get('prices', []), 'prices', nm_id)
    discounted_prices = process_price_list(item.get('discountedPrices', []), 'discountedPrices', nm_id)
    
    # Скидки
    discount = item.get('discount', 0)
    discount_on_site = item.get('discountOnSite')
    discount_on_site = discount_on_site if discount_on_site is not None else 0
    
    # Цена после СПП
    price_after_spp = calculate_price_after_spp(discounted_prices, discount_on_site)
    
    # Конкурентная цена
    competitive_price = item.get('competitivePrice', 99999)
    is_competitive_price = item.get('isCompetitivePrice', False)
    
    # Промо-акции
    promotions = item.get('promotions', [])
    has_promotions = bool(promotions and len(promotions) > 0)
    
    return {
        'nm_id': nm_id,
        'vendor_code': vendor_code,
        'price': prices,
        'discounted_price': discounted_prices,
        'discount': discount,
        'discount_on_site': discount_on_site,
        'price_after_spp': price_after_spp,
        'competitive_price': competitive_price,
        'is_competitive_price': is_competitive_price,
        'has_promotions': has_promotions
    }


def upsert_prices_to_db(goods: List[Dict[str, Any]], db_client=None) -> Dict[str, int]:
    """
    Upsert цен товаров в БД с сохранением в историю.
    
    Args:
        goods: Список товаров из WBDiscountsPricesClient.iterate_all_goods()
        db_client: Клиент БД (опционально)
        
    Returns:
        Статистика: {success: int, failed: int}
    """
    if db_client is None:
        db_client = get_client()
    
    start_time = time.time()
    success_count = 0
    failed_count = 0
    failed_items = []
    
    print(f"🚀 Начинаем upsert цен для {len(goods)} товаров...")
    
    for idx, item in enumerate(goods, 1):
        try:
            # Обработка товара
            processed = process_single_item(item)
            
            if not processed['nm_id']:
                print(f"⚠️  Пропуск товара #{idx}: отсутствует nmID")
                failed_count += 1
                continue
            
            # Upsert через функцию БД (с автоматическим сохранением в историю)
            db_client.update_prices_with_history(
                nm_id=processed['nm_id'],
                vendor_code=processed['vendor_code'],
                price=processed['price'],
                discounted_price=processed['discounted_price'],
                discount=processed['discount'],
                discount_on_site=processed['discount_on_site'],
                price_after_spp=processed['price_after_spp'],
                competitive_price=processed['competitive_price'],
                is_competitive_price=processed['is_competitive_price'],
                has_promotions=processed['has_promotions']
            )
            
            success_count += 1
            
            if idx % 50 == 0:
                print(f"📊 Обработано: {idx}/{len(goods)} ({success_count} успешно, {failed_count} ошибок)")
        
        except Exception as e:
            failed_count += 1
            failed_items.append({'nm_id': item.get('nmID'), 'error': str(e)})
            print(f"❌ Ошибка при upsert цен для {item.get('nmID')}: {e}")
    
    # Финальная статистика
    execution_time_ms = int((time.time() - start_time) * 1000)
    
    print(f"\n{'='*60}")
    print(f"✅ Upsert цен завершен:")
    print(f"   • Успешно: {success_count}")
    print(f"   • Ошибок: {failed_count}")
    print(f"   • Время выполнения: {execution_time_ms}мс ({execution_time_ms/1000:.2f}с)")
    print(f"{'='*60}\n")
    
    # Логирование в БД
    status = 'success' if failed_count == 0 else 'warning' if success_count > 0 else 'error'
    
    db_client.log_validation(
        operation_type='fetch_prices',
        status=status,
        records_processed=success_count,
        records_failed=failed_count,
        input_data={'sample': goods[0] if goods else None},
        validation_errors=failed_items if failed_items else None,
        execution_time_ms=execution_time_ms
    )
    
    return {
        'success': success_count,
        'failed': failed_count
    }


def sync_discounts_prices_to_db(api_client, db_client=None, max_goods: int = None) -> Dict[str, int]:
    """
    Полная синхронизация: получение цен из API и сохранение в БД.
    
    Args:
        api_client: WBDiscountsPricesClient instance
        db_client: Клиент БД (опционально)
        max_goods: Максимальное количество товаров для обработки
        
    Returns:
        Статистика операции
    """
    if db_client is None:
        db_client = get_client()
    
    print("📥 Получаем цены и скидки из WB API...")
    
    # Получаем товары из API
    max_pages = max_goods // 50 if max_goods else None
    
    goods = api_client.iterate_all_goods(
        page_size=50,
        sleep_seconds=1.0,
        max_pages=max_pages
    )
    
    print(f"✅ Получено {len(goods)} товаров из API")
    
    if not goods:
        print("⚠️  Нет данных для обработки")
        return {'success': 0, 'failed': 0}
    
    # Upsert в БД
    return upsert_prices_to_db(goods, db_client)


def get_price_changes_report(db_client=None, days: int = 7) -> List[Dict[str, Any]]:
    """
    Получить отчет об изменениях цен за последние N дней.
    
    Args:
        db_client: Клиент БД
        days: Количество дней для анализа
        
    Returns:
        Список товаров с изменениями цен
    """
    if db_client is None:
        db_client = get_client()
    
    # SQL запрос для получения изменений
    query = f"""
    SELECT 
        ph.nm_id,
        p.vendor_code,
        p.brand,
        COUNT(*) as changes_count,
        MIN(ph.price_after_spp) as min_price,
        MAX(ph.price_after_spp) as max_price,
        AVG(ph.price_after_spp) as avg_price
    FROM price_history ph
    JOIN products p ON ph.nm_id = p.nm_id
    WHERE ph.recorded_at >= NOW() - INTERVAL '{days} days'
    GROUP BY ph.nm_id, p.vendor_code, p.brand
    HAVING COUNT(*) > 1
    ORDER BY changes_count DESC
    """
    
    result = db_client.client.rpc('exec_sql', {'sql': query}).execute()
    return result.data


# Пример использования
if __name__ == "__main__":
    from wb_api.discounts_prices.discounts_prices import WBDiscountsPricesClient
    
    print("🧪 ТЕСТ: Синхронизация Discounts-Prices с БД")
    print("=" * 60)
    
    # Инициализация клиентов
    api_client = WBDiscountsPricesClient()
    db_client = get_client()
    
    # Тест подключения
    if not db_client.test_connection():
        print("❌ Не удалось подключиться к БД")
        exit(1)
    
    # Синхронизация (первые 100 товаров для теста)
    stats = sync_discounts_prices_to_db(
        api_client=api_client,
        db_client=db_client,
        max_goods=100
    )
    
    print(f"\n✅ Синхронизация завершена: {stats}")

