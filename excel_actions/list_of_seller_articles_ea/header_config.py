"""
Алиасы заголовков для листа "База артикулов" (list_of_seller_articles).

Требования:
- Динамический поиск колонок по алиасам для barcode и vendorCode (supplierArticle).
- Если заголовок встречается несколько раз, пишем данные во ВСЕ такие колонки.
"""

from __future__ import annotations

from typing import Tuple, Dict


def _norm(s: str) -> str:
    return " ".join(str(s).strip().lower().split())


# Алиасы для колонок
ALIASES: Dict[str, Tuple[str, ...]] = {
    # barcode
    "barcode": (
        "barcode",
        "баркод",
        "Баркод",
    ),
    # nmID (Артикул WB)
    "article": (
        "артикул",
        "Артикул",
        "nm id",
        "nmid",
        "nm",
    ),
    # vendorCode / supplierArticle (артикул продавца)
    "vendor": (
        "артикул продавца",
        "Артикул продавца",
        "артикул продаваца",
        "Артикул продаваца",
        "артикул продавца.",
    ),
    # size / размеры
    "size": (
        "size",
        "размер",
        "Размер",
        "размеры",
        "Размеры",
    ),
}


def is_alias(kind: str, title: str) -> bool:
    """Проверяет, относится ли заголовок к указанному типу алиасов."""
    title_n = _norm(title)
    return title_n in {_norm(x) for x in ALIASES.get(kind, ())}


