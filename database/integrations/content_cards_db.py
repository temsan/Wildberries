"""
Интеграция Content Cards API с базой данных.
Upsert товаров и их вариантов из WBContentCardsClient.
"""

from typing import List, Dict, Any
import time
from pathlib import Path
import sys

# Добавляем корневую директорию в path для импорта
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from database.db_client import get_client


def extract_variants_from_card(card: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Извлекает варианты (баркоды + размеры) из карточки товара.
    
    Args:
        card: Карточка товара из Content API
        
    Returns:
        Список вариантов [{"barcode": "...", "size": "..."}]
    """
    variants = []
    sizes = card.get('sizes', [])
    
    for size_item in sizes:
        # Получаем размер из techSize или wbSize
        size = size_item.get('techSize', size_item.get('wbSize', 'Без размера'))
        
        # Извлекаем баркоды
        skus = size_item.get('skus', [])
        for sku in skus:
            if isinstance(sku, str):
                barcode = sku.strip()
            elif isinstance(sku, dict):
                barcode = str(sku.get('barcode', '')).strip()
            else:
                continue
            
            if barcode:
                variants.append({"barcode": barcode, "size": size})
    
    return variants


def calculate_volume_from_dimensions(dimensions: Dict[str, Any]) -> float:
    """
    Рассчитывает объем из dimensions.
    
    Args:
        dimensions: Словарь с размерами {length, width, height} в см
        
    Returns:
        Объем в литрах
    """
    if not dimensions:
        return 0.0
    
    length = dimensions.get('length', 0)
    width = dimensions.get('width', 0)
    height = dimensions.get('height', 0)
    
    # См³ → литры (1 литр = 1000 см³)
    volume_cm3 = length * width * height
    volume_liters = volume_cm3 / 1000
    
    return round(volume_liters, 3)


def upsert_cards_to_db(cards: List[Dict[str, Any]], db_client=None) -> Dict[str, int]:
    """
    Upsert карточек товаров в БД.
    
    Args:
        cards: Список карточек из WBContentCardsClient.iterate_all_cards()
        db_client: Клиент БД (опционально, создается автоматически)
        
    Returns:
        Статистика: {success: int, failed: int, total_variants: int}
    """
    if db_client is None:
        db_client = get_client()
    
    start_time = time.time()
    success_count = 0
    failed_count = 0
    total_variants = 0
    failed_items = []
    
    print(f"🚀 Начинаем upsert {len(cards)} товаров в БД...")
    
    for idx, card in enumerate(cards, 1):
        try:
            nm_id = card.get('nmID')
            if not nm_id:
                print(f"⚠️  Пропуск карточки #{idx}: отсутствует nmID")
                failed_count += 1
                continue
            
            vendor_code = str(card.get('vendorCode', '')).strip()
            if not vendor_code:
                print(f"⚠️  Пропуск карточки #{idx} (nmID={nm_id}): отсутствует vendorCode")
                failed_count += 1
                continue
            
            brand = card.get('brand', '')
            title = card.get('title', '')
            subject = card.get('subjectName', '')
            
            # Рассчитываем объем
            dimensions = card.get('dimensions', {})
            volume = calculate_volume_from_dimensions(dimensions)
            
            # Извлекаем варианты
            variants = extract_variants_from_card(card)
            
            if not variants:
                print(f"⚠️  Товар {nm_id} не имеет баркодов, пропускаем")
                failed_count += 1
                continue
            
            # Upsert через функцию БД
            db_client.upsert_product_with_variants(
                nm_id=nm_id,
                vendor_code=vendor_code,
                brand=brand,
                title=title,
                subject=subject,
                volume=volume,
                variants=variants
            )
            
            success_count += 1
            total_variants += len(variants)
            
            if idx % 50 == 0:
                print(f"📊 Обработано: {idx}/{len(cards)} ({success_count} успешно, {failed_count} ошибок)")
        
        except Exception as e:
            failed_count += 1
            failed_items.append({'nm_id': card.get('nmID'), 'error': str(e)})
            print(f"❌ Ошибка при upsert товара {card.get('nmID')}: {e}")
    
    # Финальная статистика
    execution_time_ms = int((time.time() - start_time) * 1000)
    
    print(f"\n{'='*60}")
    print(f"✅ Upsert завершен:")
    print(f"   • Успешно: {success_count}")
    print(f"   • Ошибок: {failed_count}")
    print(f"   • Всего баркодов: {total_variants}")
    print(f"   • Время выполнения: {execution_time_ms}мс ({execution_time_ms/1000:.2f}с)")
    print(f"{'='*60}\n")
    
    # Логирование в БД
    status = 'success' if failed_count == 0 else 'warning' if success_count > 0 else 'error'
    
    db_client.log_validation(
        operation_type='fetch_articles',
        status=status,
        records_processed=success_count,
        records_failed=failed_count,
        input_data={'sample': cards[0] if cards else None},
        validation_errors=failed_items if failed_items else None,
        execution_time_ms=execution_time_ms
    )
    
    return {
        'success': success_count,
        'failed': failed_count,
        'total_variants': total_variants
    }


def sync_content_cards_to_db(api_client, db_client=None, max_cards: int = None) -> Dict[str, int]:
    """
    Полная синхронизация: получение карточек из API и сохранение в БД.
    
    Args:
        api_client: WBContentCardsClient instance
        db_client: Клиент БД (опционально)
        max_cards: Максимальное количество карточек для обработки
        
    Returns:
        Статистика операции
    """
    if db_client is None:
        db_client = get_client()
    
    print("📥 Получаем карточки товаров из WB API...")
    
    # Получаем карточки из API
    cards = api_client.iterate_all_cards(
        limit=100,
        sleep_seconds=0.7,
        max_pages=max_cards // 100 if max_cards else None
    )
    
    print(f"✅ Получено {len(cards)} карточек из API")
    
    if not cards:
        print("⚠️  Нет данных для обработки")
        return {'success': 0, 'failed': 0, 'total_variants': 0}
    
    # Upsert в БД
    return upsert_cards_to_db(cards, db_client)


# Пример использования
if __name__ == "__main__":
    from wb_api.content_cards import WBContentCardsClient, API_KEY
    
    print("🧪 ТЕСТ: Синхронизация Content Cards с БД")
    print("=" * 60)
    
    # Инициализация клиентов
    api_client = WBContentCardsClient(API_KEY)
    db_client = get_client()
    
    # Тест подключения
    if not db_client.test_connection():
        print("❌ Не удалось подключиться к БД")
        exit(1)
    
    # Синхронизация (первые 100 карточек для теста)
    stats = sync_content_cards_to_db(
        api_client=api_client,
        db_client=db_client,
        max_cards=100
    )
    
    print(f"\n✅ Синхронизация завершена: {stats}")

