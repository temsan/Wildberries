"""
Фильтр артикулов для supplier_stock: оставляет записи по списку требуемых barcode.
Совместим по интерфейсу с версией из warehouse_remains_ea.
"""

from typing import Any, Dict, List


def filter_articles_by_list(api_data: List[Dict[str, Any]], required_articles: List[str]) -> Dict[str, Any]:
    print("🔍 Фильтруем barcode по списку...")

    total_articles = len(api_data)
    required_count = len(required_articles)
    print(f"📊 Исходных записей из API: {total_articles}")
    print(f"📋 Barcode в списке для отбора: {required_count}")

    # Нормализуем список требуемых barcode к строкам
    required_set = {str(x).strip() for x in required_articles if str(x).strip()}

    filtered_data: List[Dict[str, Any]] = []
    found_articles: List[str] = []
    not_found_articles: List[str] = []

    for item in api_data:
        barcode = str(item.get('barcode', ''))
        if barcode in required_set:
            filtered_data.append(item)
            found_articles.append(barcode)
        else:
            not_found_articles.append(barcode)

    selected_count = len(filtered_data)
    missing_from_data = [req for req in required_set if req not in found_articles]

    print(f"✅ Найдено и отобрано barcode: {selected_count}")
    print(f"❌ Не найдено в списке: {total_articles - selected_count}")
    if not_found_articles:
        preview = not_found_articles[:5]
        print(f"⚠️  Примеры barcode вне списка: {preview}{'...' if len(not_found_articles)>5 else ''}")

    return {
        'filtered_data': filtered_data,
        'statistics': {
            'total_from_api': total_articles,
            'required_count': required_count,
            'selected_count': selected_count,
            'not_found_count': total_articles - selected_count,
            'missing_from_data': len(missing_from_data),
        },
        'found_articles': found_articles,
        'not_found_articles': not_found_articles,
        'missing_from_data': missing_from_data,
    }


def print_filter_statistics(result: Dict[str, Any]) -> None:
    stats = result['statistics']
    print("\n" + "=" * 50)
    print("📈 СТАТИСТИКА ОТБОРА BARCODE (supplier_stock)")
    print("=" * 50)
    print(f"📊 Исходных записей из API: {stats['total_from_api']}")
    print(f"📋 В списке для отбора: {stats['required_count']}")
    print(f"✅ Отобрано: {stats['selected_count']}")
    print(f"❌ Не в списке: {stats['not_found_count']}")
    print(f"⚠️  Отсутствуют в данных: {stats['missing_from_data']}")


