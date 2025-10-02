"""
Нормализация списка артикулов из warehouse_remains/download.
Возвращает уникальные четверки (nmId, barcode, supplierArticle, size) и пары (vendorCode, nmID).
"""

from typing import Any, Dict, Iterable, List, Tuple


def extract_triples_from_content_cards(cards: Iterable[Dict[str, Any]]) -> Tuple[List[Tuple[int, str, str, str]], List[Tuple[str, int]]]:
    """Извлекает уникальные четверки (nmID, barcode, vendorCode, size) и пары (vendorCode, nmID) из Content API.

    Важно: у одного (nmID, vendorCode) может быть несколько barcodes (разные размеры).
    Мы формируем по записи на каждый barcode из sizes[].skus (Array of strings).
    Пустые barcodes не добавляем.
    Размер берется из techSize или wbSize.
    """
    seen_quads = set()
    seen_pairs = set()
    out_quads: List[Tuple[int, str, str, str]] = []
    out_pairs: List[Tuple[str, int]] = []
    
    for card in cards:
        nm = card.get('nmID')
        if nm is None:
            continue
        nm = int(nm)
        vendor = str(card.get('vendorCode', '')).strip()
        
        # Добавляем пару (vendorCode, nmID) если она уникальна
        pair_key = (vendor, nm)
        if pair_key not in seen_pairs and vendor:  # vendor не должен быть пустым
            seen_pairs.add(pair_key)
            out_pairs.append(pair_key)
        
        sizes = card.get('sizes')
        if not isinstance(sizes, list):
            # Нет размеров/скю — пропускаем без добавления пустых баркодов
            continue
        for s in sizes:
            if not isinstance(s, dict):
                continue
                
            # Получаем размер из techSize или wbSize
            size = str(s.get('techSize', '')).strip()
            if not size:
                size = str(s.get('wbSize', '')).strip()
            if not size:
                size = 'Без размера'  # fallback для случаев без размера
                
            skus = s.get('skus')
            if not isinstance(skus, list):
                continue
            for sku in skus:
                if isinstance(sku, str):
                    barcode = sku.strip()
                elif isinstance(sku, dict):
                    barcode = str(sku.get('barcode', '')).strip()
                else:
                    continue
                if not barcode:
                    continue
                key = (nm, barcode, vendor, size)
                if key not in seen_quads:
                    seen_quads.add(key)
                    out_quads.append(key)
    return out_quads, out_pairs


