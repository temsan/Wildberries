"""
Строгая проверка структуры для базы артикулов из Content API (cards list).

Ожидаем: список карточек (list[dict]) с полями на верхнем уровне:
- nmID: int
- vendorCode: string
- sizes: list, где в sizes[i] есть поле skus (list)
  (skus могут быть строками штрихкодов или объектами, тогда barcode внутри)
"""

from typing import Any, Dict, List


def validate_report_structure(rows: List[Dict[str, Any]]) -> bool:
    print("🔍 Проверяем структуру карточек (Content API)")
    if not isinstance(rows, list):
        print("❌ Данные отчёта должны быть списком")
        return False
    if not rows:
        print("⚠️ Пустой отчёт")
        return False

    first = rows[0]
    if not isinstance(first, dict):
        print("❌ Первая запись не объект")
        return False

    # Верхний уровень
    if 'nmID' not in first or not isinstance(first['nmID'], int):
        print("❌ Нет 'nmID:int' на верхнем уровне")
        print("Доступные поля:", sorted(first.keys()))
        return False
    if 'vendorCode' not in first or not isinstance(first['vendorCode'], str):
        print("❌ Нет 'vendorCode:string' на верхнем уровне")
        print("Доступные поля:", sorted(first.keys()))
        return False
    if 'sizes' not in first or not isinstance(first['sizes'], list):
        print("❌ Нет 'sizes:list' на верхнем уровне")
        print("Доступные поля:", sorted(first.keys()))
        return False

    # sizes.skus существует
    sizes = first['sizes']
    if sizes:
        s0 = sizes[0]
        if not isinstance(s0, dict):
            print("❌ sizes[0] должен быть объектом")
            return False
        if 'skus' not in s0 or not isinstance(s0['skus'], list):
            print("❌ В sizes[0] нет 'skus:list'")
            return False
        # skus: массив строк
        skus = s0['skus']
        if skus:
            if not isinstance(skus[0], str):
                print("❌ Ожидается 'skus: Array of strings' (первый элемент не string)")
                return False

    print("✅ Структура корректна (nmID, vendorCode, sizes[].skus)")
    return True


def check_and_validate_structure(rows: List[Dict[str, Any]]) -> bool:
    # Обёртка для совместимости стиля вызова
    return validate_report_structure(rows)


