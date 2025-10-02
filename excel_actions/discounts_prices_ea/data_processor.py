"""
Обработка данных discounts_prices для формирования отчета
"""

from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


def process_discounts_data(listGoods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Обрабатывает данные discounts_prices и формирует структурированный отчет.
    
    Args:
        listGoods: Список товаров из API
        
    Returns:
        List[Dict]: Обработанные данные для отчета
    """
    
    print("🔄 Обрабатываем данные для отчета...")
    
    processed_data = []
    
    for item in listGoods:
        try:
            processed_item = process_single_item(item)
            processed_data.append(processed_item)
        except Exception as e:
            logger.error(f"Ошибка обработки товара {item.get('nmID', 'unknown')}: {e}")
            continue
    
    # 1) Сортировка по nmID (можно также сортировать по vendorCode)
    processed_data.sort(key=lambda x: x['nmID'])
    print(f"📊 Отсортировано {len(processed_data)} товаров по nmID")
    
    print(f"✅ Обработано {len(processed_data)} товаров")
    return processed_data


def process_single_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обрабатывает один товар.
    
    Args:
        item: Товар из API
        
    Returns:
        Dict: Обработанный товар
    """
    
    # Базовые поля
    processed = {
        "nmID": item.get("nmID", 0),
        "vendorCode": item.get("vendorCode", ""),
        "brand": item.get("brand", ""),
        "subject": item.get("subject", ""),
        "title": item.get("title", ""),
    }
    
    # 2) Обработка prices
    prices = item.get("prices", [])
    processed["prices"] = process_price_list(prices, "prices", processed["nmID"])
    
    # 3) Обработка discountedPrices
    discounted_prices = item.get("discountedPrices", [])
    processed["discountedPrices"] = process_price_list(discounted_prices, "discountedPrices", processed["nmID"])
    
    # 4) discount
    processed["discount"] = item.get("discount", 0)
    
    # 5) discountOnSite (может быть None)
    discount_on_site = item.get("discountOnSite")
    processed["discountOnSite"] = discount_on_site if discount_on_site is not None else 0
    
    # 6) Рассчитать цену после СПП (priceafterSPP)
    # Применяем discountOnSite к discountedPrices
    processed["priceafterSPP"] = calculate_price_after_spp(
        processed["discountedPrices"], 
        processed["discountOnSite"]
    )
    
    # 7) competitivePrice (если нет, то 99999)
    processed["competitivePrice"] = item.get("competitivePrice", 99999)
    
    # 8) isCompetitivePrice (сохраняем значение для каждого nmID)
    processed["isCompetitivePrice"] = item.get("isCompetitivePrice", False)
    
    # 9) Оценка блока promotions
    promotions = item.get("promotions", [])
    processed["hasPromotions"] = bool(promotions and len(promotions) > 0)
    
    return processed


def process_price_list(prices: List[Any], field_name: str, nmID: int) -> float:
    """
    Обрабатывает список цен (prices или discountedPrices).
    
    Args:
        prices: Список цен
        field_name: Название поля для логирования
        nmID: ID товара для логирования
        
    Returns:
        float: Обработанная цена
    """
    
    if not prices:
        return 0.0
    
    if len(prices) == 1:
        return float(prices[0])
    
    # Проверяем, одинаковые ли все цены
    unique_prices = set(prices)
    
    if len(unique_prices) == 1:
        # Все цены одинаковые
        return float(prices[0])
    else:
        # Цены разные - логируем и берем максимальную
        max_price = max(prices)
        min_price = min(prices)
        
        logger.warning(
            f"nmID {nmID}: В поле '{field_name}' установлены разные цены "
            f"для размеров: min={min_price}, max={max_price}. "
            f"Используем максимальную цену: {max_price}"
        )
        
        return float(max_price)


def calculate_price_after_spp(discounted_price: float, discount_on_site: float) -> float:
    """
    Рассчитывает цену после СПП (скидка на сайте).
    
    Args:
        discounted_price: Цена со скидкой
        discount_on_site: Дополнительная скидка на сайте (%)
        
    Returns:
        float: Цена после применения СПП
    """
    
    if not discount_on_site or discount_on_site <= 0:
        return discounted_price
    
    # Применяем скидку на сайте к цене со скидкой
    price_after_spp = discounted_price * (1 - discount_on_site / 100)
    
    return round(price_after_spp, 2)


def get_report_summary(processed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Возвращает сводку по обработанным данным.
    
    Args:
        processed_data: Обработанные данные
        
    Returns:
        Dict: Сводка отчета
    """
    
    total_items = len(processed_data)
    items_with_competitive_price = sum(1 for item in processed_data if item["competitivePrice"] != 99999)
    items_with_promotions = sum(1 for item in processed_data if item["hasPromotions"])
    items_with_spp = sum(1 for item in processed_data if item.get("discountOnSite", 0) > 0)
    
    return {
        "total_items": total_items,
        "items_with_competitive_price": items_with_competitive_price,
        "items_with_promotions": items_with_promotions,
        "items_with_spp": items_with_spp,
        "competitive_price_coverage": (items_with_competitive_price / total_items * 100) if total_items > 0 else 0,
        "promotions_coverage": (items_with_promotions / total_items * 100) if total_items > 0 else 0,
        "spp_coverage": (items_with_spp / total_items * 100) if total_items > 0 else 0
    }
