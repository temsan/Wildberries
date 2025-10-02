"""
Конфигурация заголовков для warehouse_remains Google Sheets.
"""

from __future__ import annotations

from typing import Dict, Tuple


# Строка с заголовками
HEADER_ROW_INDEX: int = 1

# Алиасы заголовков. По требованию: основной алиас — ровно "Баркод"
WAREHOUSE_HEADER_ALIASES: Dict[str, Tuple[str, ...]] = {
    "barcode": ("Баркод",),
}


