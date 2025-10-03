"""
Клиент для работы с Supabase БД.
Централизованная точка подключения и базовые операции.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from pathlib import Path
import importlib.util

# Импорт настроек из api_keys.py
BASE_DIR = Path(__file__).resolve().parents[1]
api_keys_path = BASE_DIR / "api_keys.py"
spec = importlib.util.spec_from_file_location("api_keys", str(api_keys_path))
api_keys_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(api_keys_module)

# Проверяем наличие Supabase настроек
SUPABASE_URL = getattr(api_keys_module, 'SUPABASE_URL', None)
SUPABASE_KEY = getattr(api_keys_module, 'SUPABASE_KEY', None)


class SupabaseClient:
    """Клиент для работы с Supabase БД."""
    
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """
        Инициализация клиента.
        
        Args:
            url: URL Supabase проекта (по умолчанию из api_keys.py)
            key: API key Supabase (по умолчанию из api_keys.py)
        """
        self.url = url or SUPABASE_URL
        self.key = key or SUPABASE_KEY
        
        if not self.url or not self.key:
            raise ValueError(
                "Supabase credentials not found. "
                "Add SUPABASE_URL and SUPABASE_KEY to api_keys.py or pass them as arguments."
            )
        
        try:
            from supabase import create_client
            self.client = create_client(self.url, self.key)
        except ImportError:
            raise ImportError(
                "Supabase client not installed. Run: pip install supabase"
            )
    
    def test_connection(self) -> bool:
        """
        Проверка подключения к БД.
        
        Returns:
            True если подключение успешно, False иначе
        """
        try:
            result = self.client.table('products').select('count').limit(1).execute()
            print("✅ Подключение к Supabase успешно")
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения к Supabase: {e}")
            return False
    
    # ========================================================================
    # PRODUCTS
    # ========================================================================
    
    def upsert_product(
        self,
        nm_id: int,
        vendor_code: str,
        brand: Optional[str] = None,
        title: Optional[str] = None,
        subject: Optional[str] = None,
        volume: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Upsert товара.
        
        Args:
            nm_id: Артикул WB
            vendor_code: Артикул продавца
            brand: Бренд
            title: Название
            subject: Категория
            volume: Литраж
            
        Returns:
            Результат операции
        """
        data = {
            'nm_id': nm_id,
            'vendor_code': vendor_code,
            'brand': brand,
            'title': title,
            'subject': subject,
            'volume': volume
        }
        
        return self.client.table('products').upsert(data).execute()
    
    def upsert_product_with_variants(
        self,
        nm_id: int,
        vendor_code: str,
        brand: Optional[str],
        title: Optional[str],
        subject: Optional[str],
        volume: Optional[float],
        variants: List[Dict[str, str]]
    ) -> int:
        """
        Upsert товара со всеми вариантами через функцию БД.
        
        Args:
            nm_id: Артикул WB
            vendor_code: Артикул продавца
            brand: Бренд
            title: Название
            subject: Категория
            volume: Литраж
            variants: Список вариантов [{"barcode": "...", "size": "..."}]
            
        Returns:
            nm_id обновленного товара
        """
        result = self.client.rpc(
            'upsert_product_with_variants',
            {
                'p_nm_id': nm_id,
                'p_vendor_code': vendor_code,
                'p_brand': brand,
                'p_title': title,
                'p_subject': subject,
                'p_volume': volume,
                'p_variants': variants
            }
        ).execute()
        
        return result.data
    
    def get_active_products(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получить активные товары.
        
        Args:
            limit: Лимит записей
            
        Returns:
            Список товаров
        """
        query = self.client.table('products').select('*').eq('active', True)
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        return result.data
    
    # ========================================================================
    # SELLER ARTICLES
    # ========================================================================
    
    def upsert_seller_article(
        self,
        nm_id: int,
        vendor_code: str,
        barcode: str,
        size: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upsert варианта артикула (баркода).
        
        Args:
            nm_id: Артикул WB
            vendor_code: Артикул продавца
            barcode: Штрихкод
            size: Размер
            
        Returns:
            Результат операции
        """
        data = {
            'nm_id': nm_id,
            'vendor_code': vendor_code,
            'barcode': barcode,
            'size': size
        }
        
        return self.client.table('seller_articles').upsert(data).execute()
    
    def get_active_barcodes(self, nm_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получить активные баркоды.
        
        Args:
            nm_id: Фильтр по артикулу (опционально)
            
        Returns:
            Список баркодов
        """
        query = self.client.table('seller_articles').select('*').eq('active', True)
        
        if nm_id:
            query = query.eq('nm_id', nm_id)
        
        result = query.execute()
        return result.data
    
    # ========================================================================
    # UNIT ECONOMICS (PRICES)
    # ========================================================================
    
    def update_prices_with_history(
        self,
        nm_id: int,
        vendor_code: str,
        price: Optional[float],
        discounted_price: Optional[float],
        discount: int,
        discount_on_site: Optional[int],
        price_after_spp: Optional[float],
        competitive_price: Optional[float] = None,
        is_competitive_price: bool = False,
        has_promotions: bool = False
    ) -> None:
        """
        Обновить цены с сохранением в историю.
        
        Args:
            nm_id: Артикул WB
            vendor_code: Артикул продавца
            price: Базовая цена
            discounted_price: Цена со скидкой
            discount: Скидка продавца (%)
            discount_on_site: СПП (%)
            price_after_spp: Цена после СПП
            competitive_price: Конкурентная цена
            is_competitive_price: Флаг конкурентной цены
            has_promotions: Есть промо-акции
        """
        self.client.rpc(
            'update_prices_with_history',
            {
                'p_nm_id': nm_id,
                'p_vendor_code': vendor_code,
                'p_price': price,
                'p_discounted_price': discounted_price,
                'p_discount': discount,
                'p_discount_on_site': discount_on_site,
                'p_price_after_spp': price_after_spp,
                'p_competitive_price': competitive_price or 99999,
                'p_is_competitive_price': is_competitive_price,
                'p_has_promotions': has_promotions
            }
        ).execute()
    
    def get_products_with_prices(self, only_with_prices: bool = True) -> List[Dict[str, Any]]:
        """
        Получить товары с ценами.
        
        Args:
            only_with_prices: Только товары с установленными ценами
            
        Returns:
            Список товаров с ценами
        """
        query = self.client.table('v_products_full').select('*')
        
        if only_with_prices:
            query = query.not_.is_('price', 'null')
        
        result = query.execute()
        return result.data
    
    # ========================================================================
    # WAREHOUSE REMAINS
    # ========================================================================
    
    def upsert_warehouse_remains(
        self,
        barcode: str,
        nm_id: int,
        vendor_code: str,
        warehouse_name: str,
        quantity: int,
        in_way_to_recipients: int = 0,
        in_way_returns_to_warehouse: int = 0
    ) -> Dict[str, Any]:
        """
        Upsert остатков на складе.
        
        Args:
            barcode: Штрихкод
            nm_id: Артикул WB
            vendor_code: Артикул продавца
            warehouse_name: Название склада
            quantity: Количество
            in_way_to_recipients: В пути к клиенту
            in_way_returns_to_warehouse: В пути возврат
            
        Returns:
            Результат операции
        """
        data = {
            'barcode': barcode,
            'nm_id': nm_id,
            'vendor_code': vendor_code,
            'warehouse_name': warehouse_name,
            'quantity': quantity,
            'in_way_to_recipients': in_way_to_recipients,
            'in_way_returns_to_warehouse': in_way_returns_to_warehouse
        }
        
        return self.client.table('warehouse_remains').upsert(data).execute()
    
    # ========================================================================
    # EXPORT
    # ========================================================================
    
    def get_active_articles_for_export(self) -> List[Dict[str, Any]]:
        """
        Получить активные артикулы для экспорта в Google Sheets.
        Использует view v_active_articles_export.
        
        Returns:
            Список артикулов с ценами
        """
        result = self.client.table('v_active_articles_export').select('*').execute()
        return result.data
    
    # ========================================================================
    # VALIDATION LOGS
    # ========================================================================
    
    def log_validation(
        self,
        operation_type: str,
        status: str,
        records_processed: int,
        records_failed: int = 0,
        input_data: Optional[Dict] = None,
        validation_errors: Optional[List[Dict]] = None,
        execution_time_ms: Optional[int] = None
    ) -> None:
        """
        Добавить лог валидации.
        
        Args:
            operation_type: Тип операции (fetch_articles, fetch_prices, etc)
            status: Статус (success, warning, error)
            records_processed: Количество обработанных записей
            records_failed: Количество проваленных записей
            input_data: Пример входных данных
            validation_errors: Ошибки валидации
            execution_time_ms: Время выполнения в мс
        """
        data = {
            'operation_type': operation_type,
            'status': status,
            'records_processed': records_processed,
            'records_failed': records_failed,
            'input_data': input_data,
            'validation_errors': validation_errors,
            'execution_time_ms': execution_time_ms
        }
        
        self.client.table('validation_logs').insert(data).execute()
    
    def get_recent_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Получить последние логи.
        
        Args:
            limit: Количество записей
            
        Returns:
            Список логов
        """
        result = (
            self.client.table('validation_logs')
            .select('*')
            .order('timestamp', desc=True)
            .limit(limit)
            .execute()
        )
        return result.data
    
    # ========================================================================
    # MAINTENANCE
    # ========================================================================
    
    def cleanup_old_logs(self) -> int:
        """
        Очистить старые логи (старше 30 дней).
        
        Returns:
            Количество удаленных записей
        """
        result = self.client.rpc('cleanup_old_logs').execute()
        return result.data
    
    def cleanup_old_price_history(self) -> int:
        """
        Очистить старую историю цен (старше 90 дней).
        
        Returns:
            Количество удаленных записей
        """
        result = self.client.rpc('cleanup_old_price_history').execute()
        return result.data


def get_client() -> SupabaseClient:
    """
    Получить инициализированный клиент Supabase.
    Singleton pattern для переиспользования подключения.
    
    Returns:
        SupabaseClient instance
    """
    if not hasattr(get_client, '_instance'):
        get_client._instance = SupabaseClient()
    return get_client._instance


# Пример использования
if __name__ == "__main__":
    # Инициализация
    db = get_client()
    
    # Тест подключения
    if db.test_connection():
        print("✅ Supabase готов к работе")
        
        # Пример: получить активные товары
        products = db.get_active_products(limit=5)
        print(f"📦 Активных товаров: {len(products)}")
        
        # Пример: получить последние логи
        logs = db.get_recent_logs(limit=5)
        print(f"📝 Последних логов: {len(logs)}")

