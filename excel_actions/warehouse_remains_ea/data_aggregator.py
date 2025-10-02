"""
Агрегация данных warehouse_remains по barcode.
"""

from typing import Any, Dict, List


def aggregate_warehouse_remains(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Агрегирует данные warehouse_remains по barcode.
    
    Args:
        data: Список элементов из warehouse_remains API
        
    Returns:
        List[Dict]: Агрегированные данные по каждому barcode
    """
    print("📊 Агрегируем данные warehouse_remains по barcode...")
    
    aggregated = []
    
    for item in data:
        barcode = item.get('barcode')
        if not barcode:
            print(f"⚠️ Пропускаем элемент без barcode: {item}")
            continue
        
        # Базовые данные
        aggregated_item = {
            'barcode': barcode,
            'vendorCode': item.get('vendorCode', ''),
            'nmId': item.get('nmId', 0),
            'volume': item.get('volume', 0),
            'in_way_to_recipients': 0,  # В пути до получателей
            'in_way_returns_to_warehouse': 0,  # В пути возвраты на склад WB
            'warehouses': {}  # Словарь складов: {название: количество}
        }
        
        # Обрабатываем warehouses
        warehouses = item.get('warehouses', [])
        for warehouse in warehouses:
            if not isinstance(warehouse, dict):
                continue
                
            warehouse_name = warehouse.get('warehouseName', '')
            quantity = warehouse.get('quantity', 0)
            
            # Первые два элемента - специальные показатели
            if warehouse_name == "В пути до получателей":
                aggregated_item['in_way_to_recipients'] = quantity
            elif warehouse_name == "В пути возвраты на склад WB":
                aggregated_item['in_way_returns_to_warehouse'] = quantity
            elif warehouse_name == "Всего находится на складах":
                # Игнорируем третий элемент
                continue
            else:
                # Все остальные - названия складов
                aggregated_item['warehouses'][warehouse_name] = quantity
        
        aggregated.append(aggregated_item)
    
    print(f"✅ Агрегировано {len(aggregated)} barcode")
    return aggregated


def print_aggregation_sample(aggregated_data: List[Dict[str, Any]], count: int = 3) -> None:
    """
    Выводит примеры агрегированных данных.
    
    Args:
        aggregated_data: Агрегированные данные
        count: Количество примеров для вывода
    """
    print(f"\n📋 Примеры агрегированных данных (первые {count}):")
    for i, item in enumerate(aggregated_data[:count]):
        print(f"\n{i+1}. Barcode: {item['barcode']}")
        print(f"   vendorCode: {item['vendorCode']}")
        print(f"   nmId: {item['nmId']}")
        print(f"   volume: {item['volume']}")
        print(f"   В пути до получателей: {item['in_way_to_recipients']}")
        print(f"   В пути возвраты на склад WB: {item['in_way_returns_to_warehouse']}")
        print(f"   Склады: {dict(list(item['warehouses'].items())[:3])}{'...' if len(item['warehouses']) > 3 else ''}")


def get_warehouse_statistics(aggregated_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Получает статистику по складам.
    
    Args:
        aggregated_data: Агрегированные данные
        
    Returns:
        Dict: Статистика по складам
    """
    all_warehouses = set()
    total_barcodes = len(aggregated_data)
    
    for item in aggregated_data:
        all_warehouses.update(item['warehouses'].keys())
    
    warehouse_stats = {}
    for warehouse in all_warehouses:
        count = sum(1 for item in aggregated_data if warehouse in item['warehouses'])
        warehouse_stats[warehouse] = {
            'count': count,
            'percentage': round(count / total_barcodes * 100, 1) if total_barcodes > 0 else 0
        }
    
    return {
        'total_barcodes': total_barcodes,
        'total_warehouses': len(all_warehouses),
        'warehouse_stats': warehouse_stats
    }


def get_warehouse_quantity_statistics(aggregated_data: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Получает статистику по количеству остатков на складах.
    
    Args:
        aggregated_data: Агрегированные данные
        
    Returns:
        Dict: Словарь {название_склада: общее_количество_остатков}
    """
    warehouse_quantities = {}
    
    for item in aggregated_data:
        for warehouse_name, quantity in item['warehouses'].items():
            if warehouse_name not in warehouse_quantities:
                warehouse_quantities[warehouse_name] = 0
            warehouse_quantities[warehouse_name] += quantity
    
    return warehouse_quantities


def print_warehouse_statistics(aggregated_data: List[Dict[str, Any]]) -> None:
    """
    Выводит статистику по складам.
    
    Args:
        aggregated_data: Агрегированные данные
    """
    stats = get_warehouse_statistics(aggregated_data)
    
    print(f"\n📈 СТАТИСТИКА ПО СКЛАДАМ:")
    print(f"Всего barcode: {stats['total_barcodes']}")
    print(f"Всего складов: {stats['total_warehouses']}")
    
    # Сортируем склады по количеству barcode
    sorted_warehouses = sorted(
        stats['warehouse_stats'].items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )
    
    print(f"\nТоп-10 складов по количеству barcode:")
    for i, (warehouse, stat) in enumerate(sorted_warehouses[:10]):
        print(f"{i+1:2d}. {warehouse}: {stat['count']} barcode ({stat['percentage']}%)")
    
    # Статистика по остаткам на складах
    warehouse_quantities = get_warehouse_quantity_statistics(aggregated_data)
    total_all_quantities = sum(warehouse_quantities.values())
    sorted_by_quantity = sorted(
        warehouse_quantities.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    print(f"\nТоп-10 складов по количеству остатков:")
    for i, (warehouse, total_quantity) in enumerate(sorted_by_quantity[:10]):
        percentage = (total_quantity / total_all_quantities * 100) if total_all_quantities > 0 else 0
        print(f"{i+1:2d}. {warehouse}: {total_quantity} единиц ({percentage:.1f}%)")
    
    # Дополнительная аналитика по остаткам
    print(f"\n📊 АНАЛИТИКА ПО ОСТАТКАМ:")
    
    # 1. Всего остатков на всех складах
    total_warehouse_stocks = total_all_quantities
    print(f"1. Всего остатков на всех складах: {total_warehouse_stocks:,} единиц")
    
    # 2. Всего остатков с учетом остатков в пути к и от клиента
    total_in_way_to = sum(item['in_way_to_recipients'] for item in aggregated_data)
    total_in_way_from = sum(item['in_way_returns_to_warehouse'] for item in aggregated_data)
    total_with_in_way = total_warehouse_stocks + total_in_way_to + total_in_way_from
    print(f"2. Всего остатков с учетом остатков в пути к и от клиента: {total_with_in_way:,} единиц")
    
    # 3. Количество остатков в пути к клиенту в процентном соотношении
    if total_with_in_way > 0:
        in_way_to_percentage = (total_in_way_to / total_with_in_way) * 100
        print(f"3. Количество остатков в пути к клиенту: {total_in_way_to:,} единиц ({in_way_to_percentage:.1f}%)")
    else:
        print(f"3. Количество остатков в пути к клиенту: {total_in_way_to:,} единиц (0.0%)")
    
    # 4. Количество остатков в пути от клиента в процентном соотношении
    if total_with_in_way > 0:
        in_way_from_percentage = (total_in_way_from / total_with_in_way) * 100
        print(f"4. Количество остатков в пути от клиента: {total_in_way_from:,} единиц ({in_way_from_percentage:.1f}%)")
    else:
        print(f"4. Количество остатков в пути от клиента: {total_in_way_from:,} единиц (0.0%)")
