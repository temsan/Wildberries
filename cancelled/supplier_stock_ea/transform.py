"""
Преобразования данных supplier_stocks:
1) Разрез по складам для каждого артикула (nmId, warehouseName): quantity, inWayToClient, inWayFromClient
2) Тоталы по артикулу только для inWayToClient и inWayFromClient
"""

from typing import Any, Dict, Iterable, List, Tuple


def aggregate_per_warehouse(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Группировка по (barcode, warehouseName). Суммирует количества по складу.

    Returns список словарей: {barcode, warehouseName, quantity, inWayToClient, inWayFromClient}
    """
    acc: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for r in rows:
        barcode = r.get('barcode')
        wh = r.get('warehouseName')
        if barcode is None or wh is None:
            # пропускаем некорректные записи
            continue

        key = (barcode, wh)
        if key not in acc:
            acc[key] = {
                'barcode': barcode,
                'warehouseName': wh,
                'quantity': 0,
                'inWayToClient': 0,
                'inWayFromClient': 0,
            }

        acc[key]['quantity'] += int(r.get('quantity', 0) or 0)
        acc[key]['inWayToClient'] += int(r.get('inWayToClient', 0) or 0)
        acc[key]['inWayFromClient'] += int(r.get('inWayFromClient', 0) or 0)

    # Список, отсортированный по barcode, warehouseName
    out = list(acc.values())
    out.sort(key=lambda x: (x['barcode'], x['warehouseName']))
    return out


def aggregate_inway_totals(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Тоталы по barcode: только в пути к/от клиента (без складского quantity).

    Returns список словарей: {barcode, inWayToClientTotal, inWayFromClientTotal}
    """
    acc: Dict[str, Dict[str, Any]] = {}

    for r in rows:
        barcode = r.get('barcode')
        if barcode is None:
            continue

        if barcode not in acc:
            acc[barcode] = {
                'barcode': barcode,
                'inWayToClientTotal': 0,
                'inWayFromClientTotal': 0,
            }

        acc[barcode]['inWayToClientTotal'] += int(r.get('inWayToClient', 0) or 0)
        acc[barcode]['inWayFromClientTotal'] += int(r.get('inWayFromClient', 0) or 0)

    out = list(acc.values())
    out.sort(key=lambda x: x['barcode'])
    return out


