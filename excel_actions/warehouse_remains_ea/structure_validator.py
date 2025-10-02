"""
Функции проверки структуры отчета warehouse_remains с использованием schemas.
"""

import json
import sys
import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Динамический импорт schema_utils (перенесено в excel_actions/utils/schemas)
schemas_path = Path(__file__).parent.parent / "utils" / "schemas"
schema_utils_path = schemas_path / "schema_utils.py"

if schema_utils_path.exists():
    spec = importlib.util.spec_from_file_location("schema_utils", str(schema_utils_path))
    schema_utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(schema_utils)
    load_json = schema_utils.load_json
    validate_flexible_type = schema_utils.validate_flexible_type
else:
    print("⚠️ Предупреждение: schema_utils.py не найден, используем заглушки")
    # Определяем заглушки для функций
    def load_json(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def validate_flexible_type(value, expected_type, field_name="field"):
        return True


def validate_basic_structure(item: Dict[str, Any], item_index: int = 0) -> Tuple[bool, str]:
    """
    Проверяет основные элементы базового фрейма.
    
    Args:
        item: Элемент из warehouse_remains
        item_index: Индекс элемента для отчета
        
    Returns:
        tuple[bool, str]: (True если корректна, детальная информация об ошибках)
    """
    
    # Загружаем схему из utils/schemas
    schema_path = Path(__file__).parent.parent / "utils" / "schemas" / "warehouse_remains.schema.json"
    schema = load_json(str(schema_path))
    item_structure = schema["item_structure"]
    critical_fields = schema["critical_fields"]
    optional_fields = schema["optional_fields"]
    
    errors = []
    warnings = []
    
    # Проверяем критические поля
    for field in critical_fields:
        if field not in item:
            errors.append(f"Элемент {item_index}: отсутствует критическое поле '{field}'")
            continue
            
        value = item[field]
        expected_type = item_structure[field]
        
        if not validate_flexible_type(value, expected_type):
            actual_type = type(value).__name__ if value is not None else 'null'
            errors.append(f"Элемент {item_index}: поле '{field}' имеет неправильный тип. Ожидается {expected_type}, получен {actual_type}")
    
    # Проверяем опциональные поля (только предупреждения)
    for field in optional_fields:
        if field not in item:
            warnings.append(f"Элемент {item_index}: отсутствует опциональное поле '{field}'")
        else:
            value = item[field]
            expected_type = item_structure[field]
            
            if not validate_flexible_type(value, expected_type):
                actual_type = type(value).__name__ if value is not None else 'null'
                warnings.append(f"Элемент {item_index}: поле '{field}' имеет неожиданный тип. Ожидается {expected_type}, получен {actual_type}")
    
    # Проверяем наличие других полей
    schema_fields = set(item_structure.keys())
    actual_fields = set(item.keys())
    extra_fields = actual_fields - schema_fields
    
    if extra_fields:
        warnings.append(f"Элемент {item_index}: обнаружены дополнительные поля: {', '.join(sorted(extra_fields))}")
    
    # Формируем результат
    result_messages = []
    if errors:
        result_messages.extend(errors)
    if warnings:
        result_messages.extend([f"⚠️ {w}" for w in warnings])
    
    return len(errors) == 0, "\n".join(result_messages)


def validate_warehouse_structure(item: Dict[str, Any], item_index: int = 0) -> Tuple[bool, str]:
    """
    Проверяет структуру warehouses (упрощенная версия).
    
    Args:
        item: Элемент из warehouse_remains
        item_index: Индекс элемента для отчета
        
    Returns:
        tuple[bool, str]: (True если корректна, детальная информация об ошибках)
    """
    
    warehouses = item.get('warehouses', [])
    if not isinstance(warehouses, list):
        return False, f"Элемент {item_index}: warehouses должен быть списком"
    
    errors = []
    warnings = []
    
    # Проверяем только базовую структуру каждого warehouse
    for i, warehouse in enumerate(warehouses):
        if not isinstance(warehouse, dict):
            errors.append(f"Элемент {item_index}: warehouses[{i}] должен быть словарем")
            continue
            
        # Проверяем только наличие обязательных полей
        if 'warehouseName' not in warehouse:
            errors.append(f"Элемент {item_index}: warehouses[{i}] отсутствует поле 'warehouseName'")
        
        if 'quantity' not in warehouse:
            errors.append(f"Элемент {item_index}: warehouses[{i}] отсутствует поле 'quantity'")
        
        # Проверяем типы полей (базовая проверка)
        if 'warehouseName' in warehouse and not isinstance(warehouse['warehouseName'], str):
            errors.append(f"Элемент {item_index}: warehouses[{i}].warehouseName должен быть строкой")
            
        if 'quantity' in warehouse and not isinstance(warehouse['quantity'], (int, float)):
            errors.append(f"Элемент {item_index}: warehouses[{i}].quantity должен быть числом")
    
    # Формируем результат
    result_messages = []
    if errors:
        result_messages.extend(errors)
    if warnings:
        result_messages.extend([f"⚠️ {w}" for w in warnings])
    
    return len(errors) == 0, "\n".join(result_messages)


def handle_structure_change(changes_info: str = "") -> bool:
    """
    Обрабатывает ситуацию, когда структура отчета изменилась.
    
    Args:
        changes_info: Детальная информация об изменениях
    
    Returns:
        bool: True если продолжить выполнение, False если остановить
    """
    print("\n" + "=" * 80)
    print("⚠️  ВНИМАНИЕ: Обнаружены изменения структуры отчёта warehouse_remains")
    print("=" * 80)
    
    if changes_info:
        print("🔍 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ ОБ ИЗМЕНЕНИЯХ:")
        print("-" * 60)
        print(changes_info)
        print("-" * 60)
    
    print("\n📋 ЧТО ЭТО ОЗНАЧАЕТ:")
    print("• Wildberries могли изменить формат API")
    print("• Добавились новые поля или изменились существующие")
    print("• Изменились типы данных в полях")
    print("• Это может привести к ошибкам в обработке данных")
    
    print("\n🤔 ЧТО ДЕЛАТЬ ДАЛЬШЕ?")
    print("1. Продолжить выполнение (рискованно - могут быть ошибки)")
    print("2. Остановить выполнение (безопасно - нужно обновить код)")
    
    while True:
        choice = input("\nВведите номер варианта (1 или 2): ").strip()
        if choice == "1":
            print("⚠️  Продолжаем выполнение с обновлённой структурой...")
            print("💡 Рекомендуется проверить результаты на корректность!")
            return True
        if choice == "2":
            print("🛑 Выполнение остановлено пользователем")
            print("💡 Обновите схему валидации и код для новой структуры")
            return False
        print("❌ Неверный выбор. Введите 1 или 2.")


def check_and_validate_structure(data: List[Dict[str, Any]]) -> bool:
    """
    Основная функция валидации структуры warehouse_remains.
    
    Args:
        data: Данные от warehouse_remains API
        
    Returns:
        bool: True если можно продолжать, False если нужно остановить
    """
    print("🔍 Проверяем структуру отчёта warehouse_remains...")
    
    if not isinstance(data, list):
        error_info = "Данные должны быть списком"
        print(f"\n❌ {error_info}")
        return handle_structure_change(error_info)
    
    if not data:
        print("⚠️ Пустой список товаров — нечего валидировать")
        return True
    
    # Проверяем каждый элемент
    critical_errors = []
    warnings = []
    
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            critical_errors.append(f"Элемент {i}: не является объектом (dict), получен {type(item).__name__}")
            continue
        
        # Проверяем базовую структуру
        is_valid_basic, basic_info = validate_basic_structure(item, i)
        if not is_valid_basic:
            critical_errors.append(basic_info)
        elif basic_info:  # Есть предупреждения
            warnings.append(basic_info)
        
        # Проверяем структуру warehouses
        is_valid_warehouse, warehouse_info = validate_warehouse_structure(item, i)
        if not is_valid_warehouse:
            critical_errors.append(warehouse_info)
        elif warehouse_info:  # Есть предупреждения
            warnings.append(warehouse_info)
    
    # Если есть критические ошибки - останавливаемся
    if critical_errors:
        print("\n❌ Критические ошибки в структуре:")
        error_info = "\n".join(critical_errors)
        print(error_info)
        return handle_structure_change(error_info)
    
    # Если есть только предупреждения - выводим их, но продолжаем
    if warnings:
        print("\n⚠️ Предупреждения (не критично):")
        for warning in warnings[:10]:  # Показываем только первые 10
            print(f"  • {warning}")
        if len(warnings) > 10:
            print(f"  ... и ещё {len(warnings) - 10} предупреждений")
    
    print("✅ Структура синхронизирована!")
    return True