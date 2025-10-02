"""
Main-скрипт для вызова Statistics API /api/v1/supplier/stocks.

Как выбирается dateFrom (приоритеты сверху вниз):
1) MANUAL_DATE_FROM — если указана не пустая строка, берём её
2) Аргумент --date-from — если передан при запуске
3) Дата по умолчанию: сегодня (МСК) минус 3 месяца

Запуск примеры:
  python3 WB/main_function/supplier_stock_mf/supplier_stock.py
  python3 WB/main_function/supplier_stock_mf/supplier_stock.py --date-from 2019-06-20

Параметры:
  --date-from: стартовое значение dateFrom (RFC3339)
  --max-pages: ограничение количества страниц (для теста)
  --no-throttle: отключить ожидание между запросами (НЕ рекомендуется — лимит 1/мин)
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import importlib.util

# Динамический импорт по аналогии с warehouse_remains_mf
BASE_DIR = Path(__file__).resolve().parents[2]
wb_api_path = BASE_DIR / 'wb_api' / 'supplier_stocks.py'
spec = importlib.util.spec_from_file_location("supplier_stocks", str(wb_api_path))
supplier_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(supplier_module)
WildberriesSupplierStocksAPI = supplier_module.WildberriesSupplierStocksAPI

# API ключи
api_keys_path = BASE_DIR / 'api_keys.py'
spec_keys = importlib.util.spec_from_file_location("api_keys", str(api_keys_path))
api_keys_module = importlib.util.module_from_spec(spec_keys)
spec_keys.loader.exec_module(api_keys_module)
API_KEY = api_keys_module.WB_API_TOKEN

# Импорт валидатора структуры для supplier_stock
supplier_validator_path = BASE_DIR / 'excel_actions' / 'supplier_stock_ea' / 'structure_validator.py'
spec_validator = importlib.util.spec_from_file_location("structure_validator", str(supplier_validator_path))
validator_module = importlib.util.module_from_spec(spec_validator)
spec_validator.loader.exec_module(validator_module)
check_and_validate_structure = validator_module.check_and_validate_structure

# Импорт преобразований (агрегирования)
transform_path = BASE_DIR / 'excel_actions' / 'supplier_stock_ea' / 'transform.py'
spec_transform = importlib.util.spec_from_file_location("transform", str(transform_path))
transform_module = importlib.util.module_from_spec(spec_transform)
spec_transform.loader.exec_module(transform_module)
aggregate_per_warehouse = transform_module.aggregate_per_warehouse
aggregate_inway_totals = transform_module.aggregate_inway_totals

# Импорт чтения списка артикулов и фильтра
reader_path = BASE_DIR / 'excel_actions' / 'supplier_stock_ea' / 'article_list_reader.py'
spec_reader = importlib.util.spec_from_file_location("article_list_reader", str(reader_path))
reader_module = importlib.util.module_from_spec(spec_reader)
spec_reader.loader.exec_module(reader_module)
get_article_list_from_google_sheets = reader_module.get_article_list_from_google_sheets

filter_path = BASE_DIR / 'excel_actions' / 'supplier_stock_ea' / 'article_filter.py'
spec_filter = importlib.util.spec_from_file_location("article_filter", str(filter_path))
filter_module = importlib.util.module_from_spec(spec_filter)
spec_filter.loader.exec_module(filter_module)
filter_articles_by_list = filter_module.filter_articles_by_list
print_filter_statistics = filter_module.print_filter_statistics

# Импорт райтера для Google Sheets (очистка и запись)
writer_path = BASE_DIR / 'excel_actions' / 'supplier_stock_ea' / 'google_writer.py'
spec_writer = importlib.util.spec_from_file_location("google_writer", str(writer_path))
writer_module = importlib.util.module_from_spec(spec_writer)
spec_writer.loader.exec_module(writer_module)
clear_target_cells = writer_module.clear_target_cells
write_per_warehouse_and_totals = writer_module.write_per_warehouse_and_totals


def _mask_api_key(value: Optional[str]) -> str:
    """Возвращает безопасно замаскированный ключ для логов."""
    if not value:
        return "<empty>"
    v = str(value)
    if len(v) <= 12:
        return "***"
    return f"{v[:12]}...{v[-12:]}"


def _default_date_from_msk_minus_3_months() -> str:
    """Возвращает дату по умолчанию: сегодня (МСК) минус 3 месяца, формат YYYY-MM-DD."""
    try:
        from zoneinfo import ZoneInfo  # Python 3.9+
        now_msk = datetime.now(ZoneInfo("Europe/Moscow"))
        return (now_msk - timedelta(days=90)).date().isoformat()
    except Exception:
        # Фолбэк на UTC, если zoneinfo недоступен
        return (datetime.utcnow() - timedelta(days=90)).date().isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch supplier stocks from Wildberries Statistics API")
    # По умолчанию None, чтобы не перекрывать ручной MANUAL_DATE_FROM
    parser.add_argument("--date-from", dest="date_from", default=None, help="RFC3339 dateFrom in MSK")
    parser.add_argument("--max-pages", dest="max_pages", type=int, default=None, help="Limit number of pages for testing")
    parser.add_argument("--no-throttle", dest="no_throttle", action="store_true", help="Disable 1/min throttle (NOT recommended)")
    return parser.parse_args()


def main() -> None:
    """Основная функция - ОТКЛЮЧЕНА."""
    print("=" * 80)
    print("⚠️  ФУНКЦИЯ SUPPLIER_STOCK ОТКЛЮЧЕНА")
    print("=" * 80)
    print()
    print("📋 ПРИЧИНА ОТКЛЮЧЕНИЯ:")
    print("Переходим на работу с данными из warehouse_remains API")
    print("вместо supplier_stocks (Statistics API)")
    print()
    print("🔄 РЕКОМЕНДАЦИИ:")
    print("1. Используйте warehouse_remains для получения остатков по складам:")
    print("   python3 WB/main_function/warehouse_remains_mf/warehouse_remains.py")
    print()
    print("2. Если нужно временно активировать supplier_stock:")
    print("   - Откройте файл: WB/main_function/supplier_stock_mf/supplier_stock.py")
    print("   - Найдите функцию main()")
    print("   - Закомментируйте блок предупреждения")
    print("   - Раскомментируйте оригинальную логику функции")
    print()
    print("3. Для полного удаления отключения:")
    print("   - Удалите или переименуйте этот файл")
    print("   - Обновите документацию в MAIN_FUNCTIONS.md")
    print()
    print("📊 ПРЕИМУЩЕСТВА WAREHOUSE_REMAINS:")
    print("• Более актуальные данные")
    print("• Лучшая структура данных")
    print("• Более стабильный API")
    print("• Интеграция с новой архитектурой проекта")
    print()
    print("=" * 80)
    print("🛑 ВЫПОЛНЕНИЕ ОСТАНОВЛЕНО")
    print("=" * 80)
    return


if __name__ == "__main__":
    main()


