"""
Функции проверки структуры отчёта discounts_prices API.

Особенности валидации:
1. Проверка верхнего уровня ответа (data, error, errorText, analysis, metadata)
2. Проверка структуры data.listGoods
3. Проверка критических полей товаров (nmID, vendorCode, prices, etc.)
4. Гибкая валидация с поддержкой null значений в полях скидок
5. Опциональные поля (competitivePrice, isCompetitivePrice, promotions)
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List
import importlib.util

# Динамически импортируем schema_utils по абсолютному пути
_SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "utils" / "schemas"
_SCHEMA_UTILS_PATH = _SCHEMAS_DIR / "schema_utils.py"
_spec = importlib.util.spec_from_file_location("schema_utils", str(_SCHEMA_UTILS_PATH))
schema_utils = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(schema_utils)  # type: ignore[attr-defined]

load_json = schema_utils.load_json
validate_flexible_type = schema_utils.validate_flexible_type
infer_discounts_response_schema = schema_utils.infer_discounts_response_schema
infer_discounts_data_schema = schema_utils.infer_discounts_data_schema
infer_discounts_listGoods_schema = schema_utils.infer_discounts_listGoods_schema
diff_schemas = schema_utils.diff_schemas


def validate_response_structure(response_data: Dict[str, Any]) -> tuple[bool, str]:
    """
    Проверяет структуру верхнего уровня ответа.
    
    Args:
        response_data: Данные ответа от API
        
    Returns:
        tuple[bool, str]: (True если корректна, детальная информация об ошибках)
    """
    
    # Загружаем эталонную схему
    schema_path = Path(__file__).parent.parent / "utils" / "schemas" / "discounts_prices.schema.json"
    schema = load_json(str(schema_path))
    expected_structure = schema["response_structure"]
    
    errors = []
    actual_keys = set(response_data.keys())
    expected_keys = set(expected_structure.keys())
    
    # Проверяем отсутствующие ключи
    missing_keys = expected_keys - actual_keys
    if missing_keys:
        errors.append(f"Отсутствуют ключи: {', '.join(sorted(missing_keys))}")
    
    # Проверяем лишние ключи
    extra_keys = actual_keys - expected_keys
    if extra_keys:
        errors.append(f"Добавлены новые ключи: {', '.join(sorted(extra_keys))}")
    
    # Проверяем типы существующих ключей
    type_errors = []
    for key, expected_type in expected_structure.items():
        if key in response_data:
            actual_type = type(response_data[key]).__name__
            if expected_type == "dict" and actual_type != "dict":
                type_errors.append(f"'{key}': ожидается {expected_type}, получен {actual_type}")
            elif expected_type == "list" and actual_type != "list":
                type_errors.append(f"'{key}': ожидается {expected_type}, получен {actual_type}")
            elif expected_type in ["bool", "str"] and actual_type != expected_type:
                type_errors.append(f"'{key}': ожидается {expected_type}, получен {actual_type}")
    
    if type_errors:
        errors.append("Неправильные типы данных:")
        for error in type_errors:
            errors.append(f"  • {error}")
    
    if errors:
        return False, "\n".join(errors)
    
    return True, ""


def validate_data_structure(data: Dict[str, Any]) -> tuple[bool, str]:
    """
    Проверяет структуру объекта data.
    
    Args:
        data: Объект data из ответа API
        
    Returns:
        tuple[bool, str]: (True если корректна, детальная информация об ошибках)
    """
    
    schema_path = Path(__file__).parent.parent / "utils" / "schemas" / "discounts_prices.schema.json"
    schema = load_json(str(schema_path))
    expected_structure = schema["data_structure"]
    
    errors = []
    actual_keys = set(data.keys())
    expected_keys = set(expected_structure.keys())
    
    # Проверяем отсутствующие ключи
    missing_keys = expected_keys - actual_keys
    if missing_keys:
        errors.append(f"В объекте data отсутствуют ключи: {', '.join(sorted(missing_keys))}")
    
    # Проверяем лишние ключи
    extra_keys = actual_keys - expected_keys
    if extra_keys:
        errors.append(f"В объекте data добавлены новые ключи: {', '.join(sorted(extra_keys))}")
    
    # Проверяем типы существующих ключей
    type_errors = []
    for key, expected_type in expected_structure.items():
        if key in data:
            actual_type = type(data[key]).__name__
            if expected_type == "list" and actual_type != "list":
                type_errors.append(f"'{key}': ожидается {expected_type}, получен {actual_type}")
    
    if type_errors:
        errors.append("Неправильные типы данных в объекте data:")
        for error in type_errors:
            errors.append(f"  • {error}")
    
    if errors:
        return False, "\n".join(errors)
    
    return True, ""


def validate_critical_fields(item: Dict[str, Any], item_index: int = 0) -> tuple[bool, str]:
    """
    Проверяет критические поля товара (останавливает выполнение при ошибке).
    
    Args:
        item: Товар из listGoods
        item_index: Индекс товара для отчета
        
    Returns:
        tuple[bool, str]: (True если корректны, детальная информация об ошибках)
    """
    
    schema_path = Path(__file__).parent.parent / "utils" / "schemas" / "discounts_prices.schema.json"
    schema = load_json(str(schema_path))
    critical_fields = schema["listGoods_item_critical"]
    
    errors = []
    
    for field, expected_type in critical_fields.items():
        if field not in item:
            # Проверяем, является ли поле опциональным
            if expected_type.startswith("optional_"):
                continue  # Пропускаем опциональные поля
            else:
                errors.append(f"Товар {item_index}: отсутствует критическое поле '{field}'")
                continue
        
        value = item[field]
        if not validate_flexible_type(value, expected_type):
            actual_type = type(value).__name__ if value is not None else 'null'
            errors.append(f"Товар {item_index}: поле '{field}' имеет неправильный тип. Ожидается {expected_type}, получен {actual_type}")
    
    if errors:
        return False, "\n".join(errors)
    
    return True, ""


def validate_optional_fields(item: Dict[str, Any]) -> List[str]:
    """
    Проверяет опциональные поля товара (не останавливает выполнение).
    
    Args:
        item: Товар из listGoods
        
    Returns:
        List[str]: Список предупреждений (если есть)
    """
    
    schema_path = Path(__file__).parent.parent / "utils" / "schemas" / "discounts_prices.schema.json"
    schema = load_json(str(schema_path))
    optional_fields = schema["listGoods_item_optional"]
    
    warnings = []
    
    for field, expected_type in optional_fields.items():
        if field in item:
            value = item[field]
            if not validate_flexible_type(value, expected_type):
                warnings.append(f"Поле '{field}' имеет неожиданный тип. Ожидается {expected_type}, получен {type(value).__name__ if value is not None else 'null'}")
    
    return warnings


def handle_structure_change(changes_info: str = "", interactive: bool = False) -> bool:
    """
    Обрабатывает ситуацию, когда структура отчета изменилась.
    
    Args:
        changes_info: Детальная информация об изменениях
    
    Returns:
        bool: True если продолжить выполнение, False если остановить
    """
    print("\n" + "=" * 80)
    print("⚠️  ВНИМАНИЕ: Обнаружены изменения структуры отчёта discounts_prices")
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
    
    if not interactive:
        print("\n⚙️ Нейнтерактивный режим: продолжаем выполнение (с предупреждениями)")
        return True
    
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


def check_and_validate_structure(response_data: Dict[str, Any], *, interactive: bool = False) -> bool:
    """
    Основная функция валидации структуры discounts_prices.
    
    Args:
        response_data: Полный ответ от API discounts_prices
        
    Returns:
        bool: True если можно продолжать, False если нужно остановить
    """
    print("🔍 Проверяем структуру отчёта discounts_prices...")
    
    # 1. Проверка верхнего уровня
    is_valid, error_info = validate_response_structure(response_data)
    if not is_valid:
        print("\n❌ Ошибка в структуре верхнего уровня ответа")
        return handle_structure_change(error_info, interactive=interactive)
    
    # 2. Проверка структуры data
    if "data" not in response_data:
        error_info = "Отсутствует ключ 'data' в ответе"
        print(f"\n❌ {error_info}")
        return handle_structure_change(error_info, interactive=interactive)
    
    is_valid, error_info = validate_data_structure(response_data["data"])
    if not is_valid:
        print("\n❌ Ошибка в структуре объекта data")
        return handle_structure_change(error_info, interactive=interactive)
    
    # 3. Проверка listGoods
    listGoods = response_data["data"]["listGoods"]
    if not isinstance(listGoods, list):
        error_info = "Поле 'listGoods' должно быть списком (list), получен " + type(listGoods).__name__
        print(f"\n❌ {error_info}")
        return handle_structure_change(error_info)
    
    if not listGoods:
        print("⚠️ Пустой список товаров — нечего валидировать")
        return True
    
    # 4. Проверка критических полей для каждого товара
    critical_errors = []
    optional_warnings = []
    
    for i, item in enumerate(listGoods):
        if not isinstance(item, dict):
            critical_errors.append(f"Товар {i}: не является объектом (dict), получен {type(item).__name__}")
            continue
        
        # Проверяем критические поля
        is_valid, error_info = validate_critical_fields(item, i)
        if not is_valid:
            critical_errors.append(error_info)
        
        # Проверяем опциональные поля
        warnings = validate_optional_fields(item)
        if warnings:
            optional_warnings.extend([f"Товар {i}: {w}" for w in warnings])
    
    # Если есть критические ошибки - останавливаемся
    if critical_errors:
        print("\n❌ Критические ошибки в структуре товаров:")
        error_info = "\n".join(critical_errors)
        print(error_info)
        return handle_structure_change(error_info, interactive=interactive)
    
    # Если есть только предупреждения - выводим их, но продолжаем
    if optional_warnings:
        print("\n⚠️ Предупреждения (не критично):")
        for warning in optional_warnings[:10]:  # Показываем только первые 10
            print(f"  • {warning}")
        if len(optional_warnings) > 10:
            print(f"  ... и ещё {len(optional_warnings) - 10} предупреждений")
    
    print("✅ Структура синхронизирована!")
    return True
