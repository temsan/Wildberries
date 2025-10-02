"""
Основная функция для работы с остатками товаров warehouse_remains.
Интегрирует валидацию, агрегацию и запись в Google Sheets.
"""

import sys
import json
import importlib.util
from pathlib import Path

# Базовый путь к проекту
BASE_DIR = Path(__file__).resolve().parents[2]

# Импорт API клиента
wb_api_path = BASE_DIR / 'wb_api' / 'warehouse_remains.py'
spec = importlib.util.spec_from_file_location("warehouse_remains", str(wb_api_path))
warehouse_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(warehouse_module)
WildberriesWarehouseAPI = warehouse_module.WildberriesWarehouseAPI

# Импорт валидатора структуры
structure_validator_path = BASE_DIR / 'excel_actions' / 'warehouse_remains_ea' / 'structure_validator.py'
spec = importlib.util.spec_from_file_location("structure_validator", str(structure_validator_path))
validator_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator_module)
check_and_validate_structure = validator_module.check_and_validate_structure

# Импорт агрегатора данных
data_aggregator_path = BASE_DIR / 'excel_actions' / 'warehouse_remains_ea' / 'data_aggregator.py'
spec = importlib.util.spec_from_file_location("data_aggregator", str(data_aggregator_path))
aggregator_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aggregator_module)
aggregate_warehouse_remains = aggregator_module.aggregate_warehouse_remains
print_aggregation_sample = aggregator_module.print_aggregation_sample
print_warehouse_statistics = aggregator_module.print_warehouse_statistics

# Импорт Google Sheets writer
google_sheets_writer_path = BASE_DIR / 'excel_actions' / 'warehouse_remains_ea' / 'google_sheets_writer.py'
spec = importlib.util.spec_from_file_location("google_sheets_writer", str(google_sheets_writer_path))
writer_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer_module)
write_warehouse_remains_to_sheets = writer_module.write_warehouse_remains_to_sheets

# Импорт валидатора данных
data_validator_path = BASE_DIR / 'excel_actions' / 'warehouse_remains_ea' / 'data_validator.py'
spec = importlib.util.spec_from_file_location("data_validator", str(data_validator_path))
data_validator_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_validator_module)
validate_warehouse_remains_data = data_validator_module.validate_warehouse_remains_data

# Импорт API ключей
api_keys_path = BASE_DIR / 'api_keys.py'
spec = importlib.util.spec_from_file_location("api_keys", str(api_keys_path))
api_keys_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_keys_module)
API_KEY = api_keys_module.WB_API_TOKEN
GOOGLE_SHEET_ID = api_keys_module.GOOGLE_SHEET_ID


def show_api_key_mask(api_key: str) -> None:
    """
    Показывает маску API ключа для безопасности.
    
    Args:
        api_key: API ключ для маскирования
    """
    if not api_key:
        print("🔑 API ключ: НЕ УСТАНОВЛЕН")
        return
    
    # Показываем первые 20 символов и последние 10
    if len(api_key) > 30:
        masked_key = f"{api_key[:20]}...{api_key[-10:]}"
    else:
        masked_key = f"{api_key[:10]}...{api_key[-5:]}"
    
    print(f"🔑 API ключ: {masked_key}")


def load_test_data():
    """
    Загружает тестовые данные из JSON файла для демонстрации.
    
    Returns:
        List[Dict]: Тестовые данные warehouse_remains
    """
    test_data_path = BASE_DIR / 'wb_api' / 'warehouse_remains_response.json'
    
    if not test_data_path.exists():
        print(f"❌ Тестовый файл не найден: {test_data_path}")
        return None
    
    try:
        with open(test_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"📂 Загружены тестовые данные: {len(data)} элементов")
        return data
    except Exception as e:
        print(f"❌ Ошибка при загрузке тестовых данных: {e}")
        return None


def main():
    """
    Основная функция warehouse_remains с полной интеграцией.
    
    Процесс:
    1. Получение данных из API (или загрузка тестовых)
    2. Валидация структуры данных
    3. Агрегация данных по barcode
    4. Вывод статистики и примеров
    5. Запись в Google Sheets
    """
    print("🚀 ЗАПУСК WAREHOUSE_REMAINS - ПОЛНАЯ ИНТЕГРАЦИЯ")
    print("=" * 70)
    print()
    
    # ========================================
    # 🔧 НАСТРОЙКИ (подставьте ваши данные)
    # ========================================
    
    # Показываем используемый API ключ
    print("📋 КОНФИГУРАЦИЯ:")
    show_api_key_mask(API_KEY)
    print(f"📊 Google Sheet ID: {GOOGLE_SHEET_ID}")
    print()
    
    # Настройки Google Sheets
    SHEET_NAME = "Остатки по складам"  # ⚠️ ПОДСТАВЬТЕ НАЗВАНИЕ ЛИСТА
    USE_TEST_DATA = False  # ⚠️ True = тестовые данные, False = реальный API
    
    print(f"📝 Название листа: {SHEET_NAME}")
    print(f"🧪 Тестовые данные: {USE_TEST_DATA}")
    print()
    
    # ========================================
    
    # 1. Получаем данные
    print("1️⃣ Получаем данные warehouse_remains...")
    
    if USE_TEST_DATA:
        print("📊 Используем тестовые данные")
        report_data = load_test_data()
        if not report_data:
            return
    else:
        print("🌐 Используем реальный API")
        try:
            api = WildberriesWarehouseAPI(API_KEY)
            report_data = api.get_warehouse_remains()
            
            if not report_data:
                print("❌ Не удалось получить данные об остатках")
                return
                
            print(f"✅ Получено {len(report_data)} товаров из API")
        except Exception as e:
            print(f"❌ Ошибка при получении данных из API: {e}")
            return
    
    print()
    
    # 2. Валидация структуры данных
    print("2️⃣ Валидация структуры данных...")
    if not check_and_validate_structure(report_data):
        print("🛑 Выполнение остановлено из-за проблем со структурой данных")
        return
    
    print("✅ Структура данных корректна")
    print()
    
    # 3. Агрегация данных по barcode
    print("3️⃣ Агрегация данных по barcode...")
    aggregated_data = aggregate_warehouse_remains(report_data)
    
    if not aggregated_data:
        print("❌ Не удалось агрегировать данные")
        return
    
    print()
    
    # 4. Выводим примеры агрегированных данных
    print("4️⃣ Примеры агрегированных данных:")
    print_aggregation_sample(aggregated_data, count=3)
    print()
    
    # 5. Выводим статистику по складам
    print("5️⃣ Статистика по складам:")
    print_warehouse_statistics(aggregated_data)
    print()
    
    # 6. Запись в Google Sheets
    print("6️⃣ Запись данных в Google Sheets...")
    sheet_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/edit"
    
    try:
        write_warehouse_remains_to_sheets(sheet_url, SHEET_NAME, aggregated_data)
        print("✅ Данные успешно записаны в Google Sheets")
    except Exception as e:
        print(f"❌ Ошибка при записи в Google Sheets: {e}")
        print("💡 Проверьте настройки Google Sheets и права доступа")
        return
    
    print()
    
    # 7. Валидация данных
    print("7️⃣ Валидация записанных данных...")
    try:
        validation_success = validate_warehouse_remains_data(sheet_url, SHEET_NAME, aggregated_data)
        if validation_success:
            print("✅ Валидация данных пройдена успешно")
        else:
            print("⚠️ Валидация данных завершена с предупреждениями")
    except Exception as e:
        print(f"❌ Ошибка при валидации данных: {e}")
        print("💡 Продолжаем выполнение без валидации")
    
    print()
    print("🎉 WAREHOUSE_REMAINS ЗАВЕРШЕНО УСПЕШНО!")
    print("=" * 70)


def test_validation_only():
    """
    Тестирует только валидацию на тестовых данных.
    """
    print("🧪 ТЕСТИРОВАНИЕ ВАЛИДАЦИИ")
    print("=" * 40)
    
    data = load_test_data()
    if not data:
        return
    
    print("🔍 Запускаем валидацию...")
    result = check_and_validate_structure(data)
    
    if result:
        print("✅ Валидация пройдена успешно")
    else:
        print("❌ Валидация не пройдена")


def test_aggregation_only():
    """
    Тестирует только агрегацию на тестовых данных.
    """
    print("🧪 ТЕСТИРОВАНИЕ АГРЕГАЦИИ")
    print("=" * 40)
    
    data = load_test_data()
    if not data:
        return
    
    print("📊 Запускаем агрегацию...")
    aggregated_data = aggregate_warehouse_remains(data)
    
    print(f"✅ Агрегировано {len(aggregated_data)} barcode")
    print_aggregation_sample(aggregated_data, count=3)
    print_warehouse_statistics(aggregated_data)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test-validation":
            test_validation_only()
        elif sys.argv[1] == "test-aggregation":
            test_aggregation_only()
        else:
            print("Доступные команды:")
            print("  python warehouse_remains.py                    # Полный запуск")
            print("  python warehouse_remains.py test-validation    # Только валидация")
            print("  python warehouse_remains.py test-aggregation   # Только агрегация")
    else:
        main()