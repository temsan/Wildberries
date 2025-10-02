"""
Функции проверки структуры отчёта supplier_stocks (statistics-api).

Эталон взят из первой страницы ответа (ключи):
['Discount', 'Price', 'SCCode', 'barcode', 'brand', 'category', 'inWayFromClient',
 'inWayToClient', 'isRealization', 'isSupply', 'lastChangeDate', 'nmId', 'quantity',
 'quantityFull', 'subject', 'supplierArticle', 'techSize', 'warehouseName']
"""

from typing import Any, Dict, List


EXPECTED_FIELDS = {
    'lastChangeDate': str,
    'warehouseName': str,
    'supplierArticle': str,
    'nmId': int,
    'barcode': str,
    'quantity': int,
    'inWayToClient': int,
    'inWayFromClient': int,
    'quantityFull': int,
    'category': str,
    'subject': str,
    'brand': str,
    'techSize': str,
    'Price': (int, float),
    'Discount': (int, float),
    'isSupply': bool,
    'isRealization': bool,
    'SCCode': str,
}


def validate_record_structure(record: Dict[str, Any]) -> bool:
    for field, expected_type in EXPECTED_FIELDS.items():
        if field not in record:
            print(f"❌ Отсутствует поле '{field}'")
            return False
        if not isinstance(record[field], expected_type):
            print(
                f"❌ Поле '{field}' имеет неправильный тип. Ожидается {expected_type}, получен {type(record[field])}"
            )
            return False
    return True


def check_and_validate_structure(data: List[Dict[str, Any]]) -> bool:
    print("🔍 Проверяем структуру отчёта supplier_stocks...")

    if not isinstance(data, list):
        print("❌ Ожидался список записей")
        return False
    if not data:
        print("⚠️ Пустой список записей — нечего валидировать")
        return True

    first = data[0]
    if validate_record_structure(first):
        print("✅ Структура синхронизирована!")
        return True
    else:
        print("🛑 Структура изменилась — требуется адаптация кода")
        return handle_structure_change()


def handle_structure_change() -> bool:
    """Диалог как в warehouse: спросить продолжать или остановить выполнение."""
    print("\n" + "=" * 50)
    print("⚠️  ВНИМАНИЕ: Обнаружены изменения структуры отчёта supplier_stocks")
    print("Возможные причины: изменения API, новые поля, типы и т.д.")
    print("Что делать дальше?")
    print("1. Продолжить выполнение (на свой риск)")
    print("2. Остановить выполнение")

    while True:
        choice = input("\nВведите номер варианта (1 или 2): ").strip()
        if choice == "1":
            print("⚠️  Продолжаем выполнение с обновлённой структурой...")
            return True
        if choice == "2":
            print("🛑 Выполнение остановлено пользователем")
            return False
        print("❌ Неверный выбор. Введите 1 или 2.")


