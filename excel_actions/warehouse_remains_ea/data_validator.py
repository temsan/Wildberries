"""
Функция валидации данных warehouse_remains в Google Sheets.
Сравнивает записанные данные с агрегированными данными из API.
"""

from typing import List, Dict, Any, Tuple, Set
from pathlib import Path
import importlib.util
import sys


# Импортируем все переменные из api-keys (динамический абсолютный путь)
BASE_DIR = Path(__file__).resolve().parents[2]
api_keys_path = BASE_DIR / 'api_keys.py'
spec = importlib.util.spec_from_file_location("api_keys", str(api_keys_path))
api_keys_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_keys_module)
GOOGLE_CREDENTIALS_FILE = getattr(api_keys_module, 'GOOGLE_CREDENTIALS_FILE', '')
GOOGLE_CREDENTIALS_INFO = getattr(api_keys_module, 'GOOGLE_CREDENTIALS_INFO', None)

# Импортируем header mapping utilities
header_mapping_path = Path(__file__).resolve().parents[1] / 'utils' / 'header_mapping.py'
spec_header = importlib.util.spec_from_file_location("header_mapping", str(header_mapping_path))
header_mapping_module = importlib.util.module_from_spec(spec_header)
sys.modules[spec_header.name] = header_mapping_module
spec_header.loader.exec_module(header_mapping_module)
load_header_map = header_mapping_module.load_header_map
HeaderMappingError = header_mapping_module.HeaderMappingError

# Импортируем конфиг заголовков для warehouse
config_path = Path(__file__).resolve().with_name('header_config.py')
spec_config = importlib.util.spec_from_file_location("header_config", str(config_path))
header_config = importlib.util.module_from_spec(spec_config)
spec_config.loader.exec_module(header_config)
HEADER_ROW_INDEX = header_config.HEADER_ROW_INDEX
WAREHOUSE_HEADER_ALIASES = header_config.WAREHOUSE_HEADER_ALIASES


def get_google_sheets_service():
    """Получает сервис Google Sheets."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    if GOOGLE_CREDENTIALS_INFO:
        credentials = Credentials.from_service_account_info(GOOGLE_CREDENTIALS_INFO, scopes=scopes)
    else:
        credentials = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=scopes)
    return build('sheets', 'v4', credentials=credentials)


def format_sheet_name(sheet_name: str) -> str:
    """Форматирует название листа для использования в диапазонах Google Sheets."""
    return f"'{sheet_name}'" if ' ' in sheet_name else sheet_name


def column_index_to_letter(col_index: int) -> str:
    """Преобразует индекс столбца в букву Google Sheets (A, B, C, ..., Z, AA, AB, ...)."""
    result = ""
    while col_index >= 0:
        result = chr(65 + (col_index % 26)) + result
        col_index = col_index // 26 - 1
        if col_index < 0:
            break
    return result


def extract_sheet_id(sheet_url: str) -> str:
    """Извлекает ID таблицы из URL Google Sheets."""
    try:
        if '/spreadsheets/d/' in sheet_url:
            start = sheet_url.find('/spreadsheets/d/') + len('/spreadsheets/d/')
            end = sheet_url.find('/', start)
            if end == -1:
                end = sheet_url.find('?', start)
            if end == -1:
                end = len(sheet_url)
            return sheet_url[start:end]
        return ""
    except Exception:
        return ""


def get_api_warehouses(aggregated_data: List[Dict[str, Any]]) -> Set[str]:
    """
    Извлекает список складов из агрегированных данных API.
    
    Args:
        aggregated_data: Агрегированные данные из API
        
    Returns:
        Set[str]: Множество названий складов из API
    """
    warehouses = set()
    for item in aggregated_data:
        warehouses.update(item['warehouses'].keys())
    return warehouses


def get_api_barcodes(aggregated_data: List[Dict[str, Any]]) -> Set[str]:
    """
    Извлекает список barcode из агрегированных данных API.
    
    Args:
        aggregated_data: Агрегированные данные из API
        
    Returns:
        Set[str]: Множество barcode из API
    """
    return {item['barcode'] for item in aggregated_data}


def find_barcode_rows(spreadsheet_id: str, sheet_name: str, barcodes: Set[str], header_map=None, start_row: int = 2) -> Dict[str, int]:
    """
    Находит номера строк для каждого barcode в Google Sheets.
    
    Args:
        spreadsheet_id: ID Google таблицы
        sheet_name: Название листа
        barcodes: Множество barcode для поиска
        
    Returns:
        Dict[str, int]: Словарь {barcode: row_number}
    """
    service = get_google_sheets_service()
    # Читаем столбец баркодов динамически через header_map
    if header_map is None:
        return {}
    try:
        barcode_range = header_map.build_column_range("barcode", start_row)
    except HeaderMappingError:
        return {}
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=barcode_range
    ).execute()
    
    values = result.get('values', [])
    
    # Создаем индекс barcode -> row_number
    barcode_rows = {}
    for i, row in enumerate(values):
        if row and row[0].strip():
            barcode_value = row[0].strip()
            if barcode_value in barcodes:
                # Смещение на start_row: values[0] соответствует строке start_row
                barcode_rows[barcode_value] = start_row + i
    
    return barcode_rows


def get_column_positions(spreadsheet_id: str, sheet_name: str, target_columns: Set[str]) -> Dict[str, int]:
    """
    Получает позиции столбцов в Google Sheets.
    
    Args:
        spreadsheet_id: ID Google таблицы
        sheet_name: Название листа
        target_columns: Множество названий столбцов для поиска
        
    Returns:
        Dict[str, int]: Словарь {column_name: column_index}
    """
    service = get_google_sheets_service()
    sheet_name_quoted = format_sheet_name(sheet_name)
    
    # Читаем заголовки (первая строка)
    range_headers = f"{sheet_name_quoted}!1:1"
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_headers
    ).execute()
    
    headers = result.get('values', [[]])[0] if result.get('values') else []
    
    # Находим позиции целевых столбцов
    column_positions = {}
    for i, header in enumerate(headers):
        if header in target_columns:
            column_positions[header] = i
    
    return column_positions


def read_validation_data_batch(spreadsheet_id: str, sheet_name: str, 
                              barcode_rows: Dict[str, int], 
                              column_positions: Dict[str, int]) -> Dict[str, Dict[str, Any]]:
    """
    Читает данные из Google Sheets для валидации используя batch запросы.
    
    Args:
        spreadsheet_id: ID Google таблицы
        sheet_name: Название листа
        barcode_rows: Словарь {barcode: row_number}
        column_positions: Словарь {column_name: column_index}
        
    Returns:
        Dict[str, Dict[str, Any]]: Данные из Google Sheets {barcode: {column: value}}
    """
    service = get_google_sheets_service()
    sheet_name_quoted = format_sheet_name(sheet_name)
    
    # Подготавливаем batch запросы
    ranges = []
    range_to_barcode_column = {}  # Связываем диапазон с barcode и столбцом
    
    for barcode, row_num in barcode_rows.items():
        for column_name, col_index in column_positions.items():
            col_letter = column_index_to_letter(col_index)
            range_name = f"{sheet_name_quoted}!{col_letter}{row_num}"
            ranges.append(range_name)
            range_to_barcode_column[range_name] = (barcode, column_name)
    
    # Чтение данных batch-запросом (без лишнего логирования)
    
    # Выполняем batch запрос
    try:
        result = service.spreadsheets().values().batchGet(
            spreadsheetId=spreadsheet_id,
            ranges=ranges
        ).execute()
        
        # Обрабатываем результаты
        validation_data = {}
        for barcode in barcode_rows.keys():
            validation_data[barcode] = {}
        
        value_ranges = result.get('valueRanges', [])
        for i, value_range in enumerate(value_ranges):
            range_name = ranges[i]
            barcode, column_name = range_to_barcode_column[range_name]
            
            values = value_range.get('values', [])
            if values and values[0]:
                value = values[0][0]
                # Преобразуем в число, если возможно
                try:
                    if isinstance(value, str) and value.strip():
                        # Заменяем запятую на точку для правильного парсинга float
                        normalized_value = value.replace(',', '.')
                        if '.' in normalized_value:
                            validation_data[barcode][column_name] = float(normalized_value)
                        else:
                            validation_data[barcode][column_name] = int(normalized_value)
                    else:
                        validation_data[barcode][column_name] = 0
                except (ValueError, TypeError):
                    validation_data[barcode][column_name] = 0
            else:
                validation_data[barcode][column_name] = 0
                
    except Exception as e:
        # Ошибка чтения — возвращаем пустые данные по требуемой структуре
        # Возвращаем пустые данные
        validation_data = {}
        for barcode in barcode_rows.keys():
            validation_data[barcode] = {}
            for column_name in column_positions.keys():
                validation_data[barcode][column_name] = 0
    
    return validation_data


def compare_data(api_data: List[Dict[str, Any]], 
                sheets_data: Dict[str, Dict[str, Any]], 
                api_warehouses: Set[str]) -> Dict[str, Any]:
    """
    Сравнивает данные из API с данными из Google Sheets.
    
    Args:
        api_data: Агрегированные данные из API
        sheets_data: Данные из Google Sheets
        api_warehouses: Множество складов из API
        
    Returns:
        Dict[str, Any]: Результат сравнения с детальной статистикой
    """
    # Сравниваем данные (сводный вывод будет ниже)
    
    # Создаем словарь API данных для быстрого поиска
    api_dict = {item['barcode']: item for item in api_data}
    
    comparison_results = {
        'total_barcodes': len(api_data),
        'found_in_sheets': 0,
        'missing_in_sheets': 0,
        'exact_matches': 0,
        'partial_matches': 0,
        'mismatches': 0,
        'errors': [],
        'warnings': [],
        'statistics': {
            'total_api_warehouses': len(api_warehouses),
            'total_api_quantities': 0,
            'total_sheets_quantities': 0,
            'quantity_difference': 0
        }
    }
    
    # Дополнительные поля для проверки
    additional_fields = ['В пути к клиенту', 'В пути от клиента', 'Объем упаковки']
    
    for barcode, api_item in api_dict.items():
        if barcode not in sheets_data:
            comparison_results['missing_in_sheets'] += 1
            comparison_results['errors'].append(f"Barcode {barcode} не найден в Google Sheets")
            continue
        
        comparison_results['found_in_sheets'] += 1
        sheets_item = sheets_data[barcode]
        
        # Проверяем дополнительные поля
        api_additional = {
            'В пути к клиенту': api_item.get('in_way_to_recipients', 0),
            'В пути от клиента': api_item.get('in_way_returns_to_warehouse', 0),
            'Объем упаковки': api_item.get('volume', 0)
        }
        
        # Проверяем склады
        api_warehouses_data = api_item.get('warehouses', {})
        
        # Сравниваем дополнительные поля
        additional_match = True
        for field in additional_fields:
            api_value = api_additional.get(field, 0)
            sheets_value = sheets_item.get(field, 0)
            
            # Приводим к числу для сравнения
            try:
                api_num = float(api_value) if api_value is not None else 0
                sheets_num = float(sheets_value) if sheets_value is not None else 0
                
                if abs(api_num - sheets_num) > 0.01:  # Допуск для float
                    additional_match = False
                    comparison_results['warnings'].append(
                        f"Barcode {barcode}, поле {field}: API={api_value}, Sheets={sheets_value}"
                    )
            except (ValueError, TypeError):
                # Если не удается преобразовать в число, сравниваем как строки
                if str(api_value) != str(sheets_value):
                    additional_match = False
                    comparison_results['warnings'].append(
                        f"Barcode {barcode}, поле {field}: API={api_value}, Sheets={sheets_value} (тип не совпадает)"
                    )
        
        # Сравниваем склады
        warehouses_match = True
        for warehouse in api_warehouses:
            if warehouse in api_warehouses_data:
                api_quantity = api_warehouses_data[warehouse]
                sheets_quantity = sheets_item.get(warehouse, 0)
                
                # Приводим к числу для сравнения
                try:
                    api_num = float(api_quantity) if api_quantity is not None else 0
                    sheets_num = float(sheets_quantity) if sheets_quantity is not None else 0
                    
                    if abs(api_num - sheets_num) > 0.01:  # Допуск для float
                        warehouses_match = False
                        comparison_results['warnings'].append(
                            f"Barcode {barcode}, склад {warehouse}: API={api_quantity}, Sheets={sheets_quantity}"
                        )
                except (ValueError, TypeError):
                    # Если не удается преобразовать в число, сравниваем как строки
                    if str(api_quantity) != str(sheets_quantity):
                        warehouses_match = False
                        comparison_results['warnings'].append(
                            f"Barcode {barcode}, склад {warehouse}: API={api_quantity}, Sheets={sheets_quantity} (тип не совпадает)"
                        )
        
        # Подсчитываем общие количества
        api_total = sum(api_warehouses_data.values()) + api_additional['В пути к клиенту'] + api_additional['В пути от клиента']
        sheets_total = sum(sheets_item.get(warehouse, 0) for warehouse in api_warehouses) + sheets_item.get('В пути к клиенту', 0) + sheets_item.get('В пути от клиента', 0)
        
        comparison_results['statistics']['total_api_quantities'] += api_total
        comparison_results['statistics']['total_sheets_quantities'] += sheets_total
        
        # Определяем тип совпадения
        if additional_match and warehouses_match:
            comparison_results['exact_matches'] += 1
        elif additional_match or warehouses_match:
            comparison_results['partial_matches'] += 1
        else:
            comparison_results['mismatches'] += 1
    
    # Вычисляем общую разность
    comparison_results['statistics']['quantity_difference'] = abs(
        comparison_results['statistics']['total_api_quantities'] - 
        comparison_results['statistics']['total_sheets_quantities']
    )
    
    return comparison_results


def print_validation_results(results: Dict[str, Any]) -> None:
    """
    Выводит результаты валидации данных.
    
    Args:
        results: Результаты сравнения данных
    """
    print("\n" + "="*70)
    print("📊 РЕЗУЛЬТАТЫ ВАЛИДАЦИИ ДАННЫХ")
    print("="*70)
    
    print(f"📋 Всего barcode в API: {results['total_barcodes']}")
    print(f"✅ Найдено в Google Sheets: {results['found_in_sheets']}")
    print(f"❌ Не найдено в Google Sheets: {results['missing_in_sheets']}")
    print()
    
    print("🔍 Детальное сравнение:")
    print(f"   ✅ Точные совпадения: {results['exact_matches']}")
    print(f"   ⚠️ Частичные совпадения: {results['partial_matches']}")
    print(f"   ❌ Несовпадения: {results['mismatches']}")
    print()
    
    print("📈 Статистика по количествам:")
    stats = results['statistics']
    print(f"   📊 Складов в API: {stats['total_api_warehouses']}")
    print(f"   🔢 Общее количество в API: {stats['total_api_quantities']}")
    print(f"   🔢 Общее количество в Sheets: {stats['total_sheets_quantities']}")
    print(f"   📉 Разность: {stats['quantity_difference']}")
    print()
    
    # Выводим ошибки
    if results['errors']:
        print("❌ ОШИБКИ:")
        for error in results['errors'][:10]:  # Показываем первые 10
            print(f"   • {error}")
        if len(results['errors']) > 10:
            print(f"   ... и еще {len(results['errors']) - 10} ошибок")
        print()
    
    # Выводим предупреждения
    if results['warnings']:
        print("⚠️ ПРЕДУПРЕЖДЕНИЯ:")
        for warning in results['warnings'][:10]:  # Показываем первые 10
            print(f"   • {warning}")
        if len(results['warnings']) > 10:
            print(f"   ... и еще {len(results['warnings']) - 10} предупреждений")
        print()
    
    # Общий результат
    if results['exact_matches'] == results['found_in_sheets'] and results['missing_in_sheets'] == 0:
        print("🎉 ВАЛИДАЦИЯ ПРОЙДЕНА УСПЕШНО! Все данные совпадают.")
    elif results['exact_matches'] > results['mismatches']:
        print("✅ ВАЛИДАЦИЯ ПРОЙДЕНА С ПРЕДУПРЕЖДЕНИЯМИ. Большинство данных совпадает.")
    else:
        print("❌ ВАЛИДАЦИЯ НЕ ПРОЙДЕНА. Обнаружены серьезные несовпадения.")
    
    print("="*70)


def validate_warehouse_remains_data(spreadsheet_url: str, sheet_name: str, 
                                  aggregated_data: List[Dict[str, Any]]) -> bool:
    """
    Главная функция валидации данных warehouse_remains в Google Sheets.
    
    Args:
        spreadsheet_url: URL Google таблицы
        sheet_name: Название листа
        aggregated_data: Агрегированные данные из API
        
    Returns:
        bool: True если валидация пройдена успешно, False иначе
    """
    print("🔍 ВАЛИДАЦИЯ ДАННЫХ WAREHOUSE_REMAINS В GOOGLE SHEETS")
    print("="*60)
    
    # Извлекаем ID таблицы
    spreadsheet_id = extract_sheet_id(spreadsheet_url)
    if not spreadsheet_id:
        print("❌ Ошибка: Не удалось извлечь ID таблицы из URL")
        return False
    
    # Минимизируем логирование: не выводим технические детали (ID/лист/счётчики)
    
    # Получаем склады и barcode из API
    api_warehouses = get_api_warehouses(aggregated_data)
    api_barcodes = get_api_barcodes(aggregated_data)
    
    # Без промежуточных счётчиков
    
    # Загружаем карту заголовков и валидируем наличие колонки "Баркод"
    service = get_google_sheets_service()
    try:
        header_map = load_header_map(
            service=service,
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            expected_headers=WAREHOUSE_HEADER_ALIASES,
            header_row=HEADER_ROW_INDEX,
        )
        # Убедились, что колонка найдена, не логируем детально
    except HeaderMappingError as e:
        print(f"❌ {e}")
        return False

    # Находим строки с barcode в Google Sheets (динамический столбец)
    barcode_rows = find_barcode_rows(spreadsheet_id, sheet_name, api_barcodes, header_map=header_map, start_row=2)

    # Подсветить баркоды в листе, которых нет в API
    # Опциональные подсветки пропускаем в итоговом выводе
    
    if not barcode_rows:
        print("❌ Не найдено ни одного barcode в Google Sheets")
        return False
    
    # Определяем столбцы для проверки
    target_columns = api_warehouses.copy()
    target_columns.update(['В пути к клиенту', 'В пути от клиента', 'Объем упаковки'])
    
    column_positions = get_column_positions(spreadsheet_id, sheet_name, target_columns)
    
    # Читаем данные из Google Sheets
    sheets_data = read_validation_data_batch(spreadsheet_id, sheet_name, barcode_rows, column_positions)
    
    # Сравниваем данные
    comparison_results = compare_data(aggregated_data, sheets_data, api_warehouses)
    
    # Выводим результаты
    print_validation_results(comparison_results)
    
    # Возвращаем результат валидации
    return (comparison_results['exact_matches'] == comparison_results['found_in_sheets'] and 
            comparison_results['missing_in_sheets'] == 0)


if __name__ == "__main__":
    # Тестирование функции
    print("🧪 ТЕСТИРОВАНИЕ ФУНКЦИИ ВАЛИДАЦИИ")
    print("="*50)
    
    # Здесь можно добавить тестовые данные для проверки
    print("Функция готова к использованию!")
