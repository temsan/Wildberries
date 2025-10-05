"""
Улучшенная интеграция Discounts-Prices API с базой данных.
Полная замена Google Sheets на прямую работу с БД.
"""

from typing import List, Dict, Any, Optional
import time
import json
from pathlib import Path
import sys
from datetime import datetime

# Добавляем корневую директорию в path для импорта
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from database.db_client import get_client
from wb_api.discounts_prices.discounts_prices import WBDiscountsPricesClient


class DiscountsPricesDBProcessor:
    """
    Обработчик для синхронизации Discounts-Prices API с БД.
    Заменяет Google Sheets интеграцию.
    """
    
    def __init__(self, db_client=None):
        """
        Инициализация процессора.
        
        Args:
            db_client: Клиент БД (опционально)
        """
        self.db_client = db_client or get_client()
        self.api_client = WBDiscountsPricesClient()
        
    def test_connections(self) -> Dict[str, bool]:
        """
        Проверяет подключения к API и БД.
        
        Returns:
            Словарь с результатами проверки
        """
        results = {
            'database': False,
            'api': False
        }
        
        # Проверка БД
        try:
            results['database'] = self.db_client.test_connection()
        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}")
        
        # Проверка API
        try:
            # Пробуем получить одну страницу
            test_data = self.api_client.fetch_goods_filtered(limit=1)
            results['api'] = bool(test_data.get('data', {}).get('listGoods'))
        except Exception as e:
            print(f"❌ Ошибка подключения к API: {e}")
        
        return results
    
    def process_price_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обрабатывает данные одного товара из API.
        
        Args:
            item: Товар из Discounts-Prices API
            
        Returns:
            Обработанные данные для БД
        """
        nm_id = item.get('nmID', 0)
        vendor_code = item.get('vendorCode', '')
        
        # Обработка цен
        prices = self._process_price_list(item.get('prices', []), 'prices', nm_id)
        discounted_prices = self._process_price_list(item.get('discountedPrices', []), 'discountedPrices', nm_id)
        
        # Скидки
        discount = item.get('discount', 0)
        discount_on_site = item.get('discountOnSite', 0)
        
        # Цена после СПП
        price_after_spp = self._calculate_price_after_spp(discounted_prices, discount_on_site)
        
        # Конкурентная цена
        competitive_price = item.get('competitivePrice', 99999)
        is_competitive_price = item.get('isCompetitivePrice', False)
        
        # Промо-акции
        promotions = item.get('promotions', [])
        has_promotions = bool(promotions and len(promotions) > 0)
        
        # Данные продукта для создания/обновления
        product_data = {
            'nm_id': nm_id,
            'vendor_code': vendor_code,
            'brand': item.get('brand', ''),
            'title': item.get('title', ''),
            'subject': item.get('subject', ''),
            'volume': item.get('volume', 0.0),
            'active': True  # По умолчанию активный
        }
        
        return {
            # Данные продукта
            **product_data,
            
            # Данные цен
            'price': prices,
            'discounted_price': discounted_prices,
            'discount': discount,
            'discount_on_site': discount_on_site,
            'price_after_spp': price_after_spp,
            'competitive_price': competitive_price,
            'is_competitive_price': is_competitive_price,
            'has_promotions': has_promotions,
            
            # Метаданные
            'raw_data': item,  # Сохраняем исходные данные для отладки
            'variants': self._extract_variants(item)  # Варианты товара (баркоды)
        }
    
    def _process_price_list(self, prices: List[Any], field_name: str, nm_id: int) -> float:
        """
        Обрабатывает список цен.
        
        Args:
            prices: Список цен
            field_name: Название поля
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
    
    def _calculate_price_after_spp(self, discounted_price: float, discount_on_site: float) -> float:
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
    
    def _extract_variants(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Извлекает варианты товара (баркоды = размеры) из данных API.
        
        Бизнес-логика:
        - Баркод = Размер товара (M, L, XL)
        - Управление = По артикулу (nmID) целиком
        - Цены = Общие для всех размеров
        
        Args:
            item: Товар из Discounts-Prices API
            
        Returns:
            Список вариантов товара (баркоды-размеры)
        """
        variants = []
        
        # Получаем баркоды из разных возможных полей API
        barcodes = item.get('barcodes', [])
        if not barcodes:
            barcodes = item.get('barcode', [])
        
        # Если баркод один (строка), делаем список
        if isinstance(barcodes, str):
            barcodes = [barcodes]
        
        # Если баркод один (число), делаем список
        if isinstance(barcodes, (int, float)):
            barcodes = [str(barcodes)]
        
        # Получаем размеры - могут быть в разных полях
        sizes = item.get('sizes', [])
        if not sizes:
            sizes = item.get('size', [])
            if sizes and isinstance(sizes, str):
                sizes = [sizes]
        
        # Если размеров нет, пробуем получить из других полей
        if not sizes:
            single_size = item.get('techSize', item.get('wbSize', ''))
            if single_size:
                sizes = [single_size]
        
        # Обрабатываем каждый баркод как отдельный размер
        for i, barcode in enumerate(barcodes):
            if barcode and str(barcode).strip():  # Пропускаем пустые баркоды
                # Определяем размер для этого баркода
                size = ''
                if i < len(sizes):
                    size = sizes[i]
                elif sizes:
                    size = sizes[0]  # Используем первый размер для всех
                else:
                    # Генерируем размер на основе индекса
                    size_options = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
                    size = size_options[i] if i < len(size_options) else f'Size_{i+1}'
                
                variant = {
                    'barcode': str(barcode).strip(),
                    'size': str(size).strip(),
                    'active': True
                }
                variants.append(variant)
        
        # Если нет баркодов, создаем один вариант с генерацией
        if not variants:
            nm_id = item.get('nmID', 0)
            vendor_code = item.get('vendorCode', '')
            
            # Генерируем баркод на основе nmID и vendorCode
            generated_barcode = f"{nm_id}_{vendor_code}_default" if nm_id else "unknown_barcode"
            
            # Определяем размер
            size = item.get('size', item.get('techSize', item.get('wbSize', 'M')))
            
            variants.append({
                'barcode': generated_barcode,
                'size': str(size).strip() if size else 'M',
                'active': True
            })
            
            print(f"⚠️  nmID {nm_id}: Нет баркодов в API, создан: {generated_barcode} (размер: {size})")
        
        return variants
    
    def sync_prices_to_db(
        self, 
        max_goods: Optional[int] = None,
        batch_size: int = 50,
        sleep_seconds: float = 1.0
    ) -> Dict[str, Any]:
        """
        Полная синхронизация цен с БД.
        
        Args:
            max_goods: Максимальное количество товаров
            batch_size: Размер батча для обработки
            sleep_seconds: Задержка между запросами к API
            
        Returns:
            Статистика синхронизации
        """
        start_time = time.time()
        
        print(f"🚀 Начинаем синхронизацию цен с БД...")
        print(f"   • Максимум товаров: {max_goods or 'без ограничений'}")
        print(f"   • Размер батча: {batch_size}")
        print(f"   • Задержка: {sleep_seconds}с")
        
        # Проверяем подключения
        connections = self.test_connections()
        if not connections['database']:
            raise Exception("Нет подключения к БД")
        if not connections['api']:
            raise Exception("Нет подключения к API")
        
        print("✅ Подключения проверены")
        
        # Получаем товары из API
        print("📥 Получаем данные из Discounts-Prices API...")
        
        max_pages = max_goods // batch_size if max_goods else None
        
        try:
            goods = self.api_client.iterate_all_goods(
                page_size=batch_size,
                sleep_seconds=sleep_seconds,
                max_pages=max_pages
            )
        except Exception as e:
            print(f"❌ Ошибка получения данных из API: {e}")
            raise
        
        print(f"✅ Получено {len(goods)} товаров из API")
        
        if not goods:
            print("⚠️  Нет данных для обработки")
            return {
                'success': 0,
                'failed': 0,
                'total': 0,
                'execution_time_ms': 0
            }
        
        # Обрабатываем товары
        return self._process_goods_batch(goods, start_time)
    
    def _process_goods_batch(self, goods: List[Dict[str, Any]], start_time: float) -> Dict[str, Any]:
        """
        Обрабатывает батч товаров и сохраняет в БД.
        
        Args:
            goods: Список товаров из API
            start_time: Время начала обработки
            
        Returns:
            Статистика обработки
        """
        success_count = 0
        failed_count = 0
        failed_items = []
        
        print(f"🔄 Обрабатываем {len(goods)} товаров...")
        
        for idx, item in enumerate(goods, 1):
            try:
                # Обработка товара
                processed = self.process_price_data(item)
                
                if not processed['nm_id']:
                    print(f"⚠️  Пропуск товара #{idx}: отсутствует nmID")
                    failed_count += 1
                    continue
                
                # 1. Создаем/обновляем продукт с размерами (баркодами)
                # Каждый баркод = отдельный размер (M, L, XL)
                # Управление ведется по артикулу (nmID) целиком
                self.db_client.rpc('upsert_product_with_variants', {
                    'p_nm_id': processed['nm_id'],
                    'p_vendor_code': processed['vendor_code'],
                    'p_brand': processed['brand'],
                    'p_title': processed['title'],
                    'p_subject': processed['subject'],
                    'p_volume': processed['volume'],
                    'p_variants': json.dumps(processed['variants'])  # [{barcode: "123", size: "M"}, ...]
                }).execute()
                
                # 2. Сохраняем цены для всего артикула
                # Цены общие для всех размеров (M, L, XL)
                # Никто не настраивает отдельные цены для размеров
                self.db_client.rpc('update_prices_with_history', {
                    'p_nm_id': processed['nm_id'],
                    'p_vendor_code': processed['vendor_code'],
                    'p_price': processed['price'],
                    'p_discounted_price': processed['discounted_price'],
                    'p_discount': processed['discount'],
                    'p_discount_on_site': processed['discount_on_site'],
                    'p_price_after_spp': processed['price_after_spp'],
                    'p_competitive_price': processed['competitive_price'],
                    'p_is_competitive_price': processed['is_competitive_price'],
                    'p_has_promotions': processed['has_promotions']
                }).execute()
                
                success_count += 1
                
                if idx % 50 == 0:
                    print(f"📊 Обработано: {idx}/{len(goods)} ({success_count} успешно, {failed_count} ошибок)")
            
            except Exception as e:
                failed_count += 1
                failed_items.append({
                    'nm_id': item.get('nmID'), 
                    'error': str(e),
                    'item': item
                })
                print(f"❌ Ошибка при обработке {item.get('nmID')}: {e}")
        
        # Финальная статистика
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        stats = {
            'success': success_count,
            'failed': failed_count,
            'total': len(goods),
            'execution_time_ms': execution_time_ms
        }
        
        self._log_sync_results(stats, failed_items, goods[0] if goods else None)
        
        return stats
    
    def _log_sync_results(
        self, 
        stats: Dict[str, Any], 
        failed_items: List[Dict], 
        sample_item: Optional[Dict]
    ) -> None:
        """
        Логирует результаты синхронизации в БД.
        
        Args:
            stats: Статистика обработки
            failed_items: Список ошибок
            sample_item: Пример товара для логов
        """
        try:
            status = 'success' if stats['failed'] == 0 else 'warning' if stats['success'] > 0 else 'error'
            
            self.db_client.rpc('log_validation', {
                'operation_type': 'sync_discounts_prices',
                'status': status,
                'records_processed': stats['success'],
                'records_failed': stats['failed'],
                'input_data': {'sample': sample_item} if sample_item else None,
                'validation_errors': failed_items if failed_items else None,
                'execution_time_ms': stats['execution_time_ms']
            }).execute()
            
        except Exception as e:
            print(f"⚠️  Ошибка логирования: {e}")
        
        # Выводим итоговую статистику
        print(f"\n{'='*60}")
        print(f"✅ Синхронизация завершена:")
        print(f"   • Всего товаров: {stats['total']}")
        print(f"   • Успешно: {stats['success']}")
        print(f"   • Ошибок: {stats['failed']}")
        print(f"   • Время выполнения: {stats['execution_time_ms']}мс ({stats['execution_time_ms']/1000:.2f}с)")
        print(f"   • Статус: {status}")
        print(f"{'='*60}\n")
    
    def get_price_analytics(self, days: int = 7) -> Dict[str, Any]:
        """
        Получает аналитику по ценам.
        
        Args:
            days: Количество дней для анализа
            
        Returns:
            Аналитические данные
        """
        try:
            # Общая статистика
            stats_query = """
            SELECT 
                COUNT(*) as total_products,
                AVG(price) as avg_price,
                MIN(price) as min_price,
                MAX(price) as max_price,
                COUNT(CASE WHEN discount > 0 THEN 1 END) as products_with_discount,
                AVG(CASE WHEN discount > 0 THEN discount END) as avg_discount
            FROM unit_economics ue
            JOIN products p ON ue.nm_id = p.nm_id
            WHERE p.active = true
            """
            
            stats_result = self.db_client.client.rpc('exec_sql', {'sql': stats_query}).execute()
            stats = stats_result.data[0] if stats_result.data else {}
            
            # Топ изменений цен
            changes_query = f"""
            SELECT 
                ph.nm_id,
                p.vendor_code,
                p.brand,
                COUNT(*) as changes_count,
                MIN(ph.price_after_spp) as min_price,
                MAX(ph.price_after_spp) as max_price,
                (MAX(ph.price_after_spp) - MIN(ph.price_after_spp)) as price_difference
            FROM price_history ph
            JOIN products p ON ph.nm_id = p.nm_id
            WHERE ph.recorded_at >= NOW() - INTERVAL '{days} days'
            GROUP BY ph.nm_id, p.vendor_code, p.brand
            HAVING COUNT(*) > 1
            ORDER BY changes_count DESC
            LIMIT 10
            """
            
            changes_result = self.db_client.client.rpc('exec_sql', {'sql': changes_query}).execute()
            
            return {
                'statistics': stats,
                'price_changes': changes_result.data,
                'analysis_period_days': days
            }
            
        except Exception as e:
            print(f"❌ Ошибка получения аналитики: {e}")
            return {'error': str(e)}
    
    def get_products_overview(self) -> Dict[str, Any]:
        """
        Получает обзор продуктов в БД с иерархией: nmID → vendorCode → barcodes.
        
        Returns:
            Обзор продуктов
        """
        try:
            # Статистика продуктов (nmID)
            products_query = """
            SELECT 
                COUNT(*) as total_products,
                COUNT(CASE WHEN active = true THEN 1 END) as active_products,
                COUNT(DISTINCT brand) as unique_brands,
                COUNT(DISTINCT subject) as unique_subjects,
                AVG(volume) as avg_volume
            FROM products
            """
            
            products_result = self.db_client.client.rpc('exec_sql', {'sql': products_query}).execute()
            products_stats = products_result.data[0] if products_result.data else {}
            
            # Статистика по артикулам продавца (vendorCode)
            vendor_codes_query = """
            SELECT 
                COUNT(DISTINCT vendor_code) as unique_vendor_codes,
                COUNT(*) as total_vendor_code_records
            FROM products
            WHERE vendor_code IS NOT NULL AND vendor_code != ''
            """
            
            vendor_codes_result = self.db_client.client.rpc('exec_sql', {'sql': vendor_codes_query}).execute()
            vendor_codes_stats = vendor_codes_result.data[0] if vendor_codes_result.data else {}
            
            # Статистика по баркодам (barcodes)
            barcodes_query = """
            SELECT 
                COUNT(*) as total_barcodes,
                COUNT(CASE WHEN active = true THEN 1 END) as active_barcodes,
                COUNT(DISTINCT barcode) as unique_barcodes
            FROM seller_articles
            """
            
            barcodes_result = self.db_client.client.rpc('exec_sql', {'sql': barcodes_query}).execute()
            barcodes_stats = barcodes_result.data[0] if barcodes_result.data else {}
            
            # Иерархия: товары с количеством баркодов
            hierarchy_query = """
            SELECT 
                p.nm_id,
                p.vendor_code,
                p.brand,
                p.title,
                COUNT(sa.id) as barcodes_count,
                COUNT(CASE WHEN sa.active = true THEN 1 END) as active_barcodes_count
            FROM products p
            LEFT JOIN seller_articles sa ON p.nm_id = sa.nm_id
            WHERE p.active = true
            GROUP BY p.nm_id, p.vendor_code, p.brand, p.title
            ORDER BY barcodes_count DESC
            LIMIT 20
            """
            
            hierarchy_result = self.db_client.client.rpc('exec_sql', {'sql': hierarchy_query}).execute()
            
            # Топ брендов с детализацией по баркодам
            brands_query = """
            SELECT 
                brand,
                COUNT(DISTINCT p.nm_id) as products_count,
                COUNT(DISTINCT p.vendor_code) as vendor_codes_count,
                COUNT(sa.id) as barcodes_count
            FROM products p
            LEFT JOIN seller_articles sa ON p.nm_id = sa.nm_id
            WHERE p.active = true AND brand IS NOT NULL AND brand != ''
            GROUP BY brand
            ORDER BY products_count DESC
            LIMIT 10
            """
            
            brands_result = self.db_client.client.rpc('exec_sql', {'sql': brands_query}).execute()
            
            return {
                'hierarchy_summary': {
                    'products': products_stats,
                    'vendor_codes': vendor_codes_stats,
                    'barcodes': barcodes_stats
                },
                'products_with_barcodes': hierarchy_result.data,
                'top_brands': brands_result.data
            }
            
        except Exception as e:
            print(f"❌ Ошибка получения обзора продуктов: {e}")
            return {'error': str(e)}
    
    def export_to_json(self, output_file: str, max_goods: Optional[int] = None) -> bool:
        """
        Экспортирует данные в JSON файл (альтернатива Google Sheets).
        
        Args:
            output_file: Путь к выходному файлу
            max_goods: Максимальное количество товаров
            
        Returns:
            Успешность операции
        """
        try:
            print(f"📤 Экспортируем данные в {output_file}...")
            
            # Получаем товары из API
            max_pages = max_goods // 50 if max_goods else None
            
            goods = self.api_client.iterate_all_goods(
                page_size=50,
                sleep_seconds=1.0,
                max_pages=max_pages
            )
            
            # Обрабатываем данные
            processed_goods = []
            for item in goods:
                processed = self.process_price_data(item)
                processed_goods.append(processed)
            
            # Сохраняем в файл
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'export_date': datetime.now().isoformat(),
                    'total_items': len(processed_goods),
                    'data': processed_goods
                }, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Экспорт завершен: {len(processed_goods)} товаров в {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка экспорта: {e}")
            return False


# Функции для обратной совместимости
def sync_discounts_prices_to_db(api_client=None, db_client=None, max_goods: int = None) -> Dict[str, int]:
    """
    Функция обратной совместимости.
    """
    processor = DiscountsPricesDBProcessor(db_client)
    stats = processor.sync_prices_to_db(max_goods)
    return {'success': stats['success'], 'failed': stats['failed']}


# Пример использования
if __name__ == "__main__":
    print("🧪 ТЕСТ: Улучшенная синхронизация Discounts-Prices с БД")
    print("=" * 70)
    
    # Инициализация процессора
    processor = DiscountsPricesDBProcessor()
    
    # Проверка подключений
    print("🔍 Проверяем подключения...")
    connections = processor.test_connections()
    
    if not connections['database']:
        print("❌ Нет подключения к БД")
        exit(1)
    
    if not connections['api']:
        print("❌ Нет подключения к API")
        exit(1)
    
    print("✅ Все подключения работают")
    
    # Тестовая синхронизация (первые 100 товаров)
    print("\n🚀 Запускаем тестовую синхронизацию...")
    stats = processor.sync_prices_to_db(max_goods=100)
    
    print(f"\n📊 Результат: {stats}")
    
    # Получаем обзор продуктов с иерархией
    print("\n📊 Получаем обзор продуктов...")
    overview = processor.get_products_overview()
    
    if 'error' not in overview:
        hierarchy = overview['hierarchy_summary']
        print(f"📊 Иерархия продуктов:")
        print(f"   • Продукты (nmID): {hierarchy['products'].get('total_products', 0)}")
        print(f"   • Артикулы продавца: {hierarchy['vendor_codes'].get('unique_vendor_codes', 0)}")
        print(f"   • Баркоды: {hierarchy['barcodes'].get('total_barcodes', 0)}")
        print(f"   • Уникальных баркодов: {hierarchy['barcodes'].get('unique_barcodes', 0)}")
        
        # Показываем примеры товаров с баркодами
        if overview['products_with_barcodes']:
            print(f"\n📦 Примеры товаров с баркодами:")
            for item in overview['products_with_barcodes'][:5]:
                print(f"   • {item['nm_id']} ({item['vendor_code']}): {item['barcodes_count']} баркодов")
    
    # Получаем аналитику цен
    print("\n📈 Получаем аналитику цен...")
    analytics = processor.get_price_analytics(days=7)
    
    if 'error' not in analytics:
        print(f"💰 Аналитика цен за 7 дней:")
        print(f"   • Товаров с ценами: {analytics['statistics'].get('total_products', 0)}")
        print(f"   • Средняя цена: {analytics['statistics'].get('avg_price', 0):.2f} ₽")
        print(f"   • Товаров со скидками: {analytics['statistics'].get('products_with_discount', 0)}")
        print(f"   • Изменений цен: {len(analytics['price_changes'])}")
    
    # Тест экспорта
    print("\n📤 Тестируем экспорт...")
    export_success = processor.export_to_json(
        "exports/discounts_prices_test.json", 
        max_goods=50
    )
    
    if export_success:
        print("✅ Экспорт успешен")
    else:
        print("❌ Экспорт не удался")
    
    print("\n🎉 Тест завершен!")
