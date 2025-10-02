from __future__ import annotations

"""
schema_utils: утилиты для работы с эталонными схемами ответов API.

Зачем нужен:
- Инференс типов полей (ключ -> тип) по актуальному ответу
- Сравнение с эталоном (added/removed/type_changed)
- Сохранение/загрузка JSON-эталонов

Как использовать в мейне (preflight):
1) сделать запрос -> получить data
2) извлечь cards/cursor
3) infer_*_schema -> получить актуальные схемы
4) load_json эталона и diff_schemas -> вывести отличия
5) при необходимости обновить эталон (save_json)
"""

import json
from typing import Any, Dict, List, Tuple
from collections import defaultdict


def _pytype_to_str(v: Any) -> str:
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "str"
    if v is None:
        return "NoneType"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "dict"
    return type(v).__name__


def _pytype_to_flexible_str(v: Any) -> str:
    """Расширенная функция для определения типов с поддержкой null значений."""
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "str"
    if v is None:
        return "null"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "dict"
    return type(v).__name__


def _determine_flexible_type(values: list) -> str:
    """Определяет гибкий тип для поля на основе списка значений."""
    types = set()
    for v in values:
        if v is not None:
            types.add(_pytype_to_flexible_str(v))
        else:
            types.add("null")
    
    if len(types) == 1:
        return list(types)[0]
    elif "null" in types and len(types) == 2:
        # Если есть null + один другой тип
        other_type = [t for t in types if t != "null"][0]
        return f"null_or_{other_type}"
    else:
        return "mixed"


def infer_cards_item_schema(cards: List[Dict[str, Any]]) -> Dict[str, str]:
    """Infer flat key->type schema for a cards[] item based on the first item."""
    if not cards:
        return {}
    first = cards[0]
    if not isinstance(first, dict):
        return {}
    schema: Dict[str, str] = {}
    for k, v in first.items():
        schema[k] = _pytype_to_str(v)
    return schema


def infer_cursor_schema(cursor: Any) -> Dict[str, str]:
    if not isinstance(cursor, dict):
        return {}
    return {k: _pytype_to_str(v) for k, v in cursor.items()}


def diff_schemas(expected: Dict[str, str], actual: Dict[str, str]) -> Dict[str, List[str]]:
    added = sorted([k for k in actual.keys() if k not in expected])
    removed = sorted([k for k in expected.keys() if k not in actual])
    type_changed = sorted([k for k in actual.keys() if k in expected and expected[k] != actual[k]])
    return {"added": added, "removed": removed, "type_changed": type_changed}


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def infer_discounts_response_schema(response_data: Dict[str, Any]) -> Dict[str, str]:
    """Определяет схему верхнего уровня ответа discounts_prices."""
    if not isinstance(response_data, dict):
        return {}
    return {k: _pytype_to_str(v) for k, v in response_data.items()}


def infer_discounts_data_schema(data: Dict[str, Any]) -> Dict[str, str]:
    """Определяет схему объекта data в ответе discounts_prices."""
    if not isinstance(data, dict):
        return {}
    return {k: _pytype_to_str(v) for k, v in data.items()}


def infer_discounts_listGoods_schema(listGoods: List[Dict[str, Any]]) -> Dict[str, str]:
    """Определяет схему товара в listGoods с учетом всех товаров для гибких типов."""
    if not listGoods:
        return {}
    
    # Собираем все значения для каждого поля
    field_values = defaultdict(list)
    for item in listGoods:
        for key, value in item.items():
            field_values[key].append(value)
    
    # Определяем тип для каждого поля
    schema = {}
    for field, values in field_values.items():
        schema[field] = _determine_flexible_type(values)
    
    return schema


def validate_flexible_type(value: Any, expected_type: str) -> bool:
    """Проверяет значение против гибкого типа (с поддержкой null_or_*)."""
    if expected_type.startswith("null_or_"):
        base_type = expected_type[8:]  # убираем "null_or_"
        return value is None or _pytype_to_flexible_str(value) == base_type
    elif expected_type.startswith("optional_"):
        # Опциональные поля могут отсутствовать
        return True
    elif expected_type.startswith("optional_null_or_"):
        # Опциональные поля с null могут отсутствовать или быть null/типом
        base_type = expected_type[17:]  # убираем "optional_null_or_"
        return value is None or _pytype_to_flexible_str(value) == base_type
    elif expected_type == "int_or_float":
        # Специальный тип для volume - может быть int или float
        return isinstance(value, (int, float))
    else:
        return _pytype_to_flexible_str(value) == expected_type


