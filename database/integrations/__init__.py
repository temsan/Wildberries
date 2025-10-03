"""
Интеграционные модули для работы с БД.
"""

from .content_cards_db import (
    upsert_cards_to_db,
    sync_content_cards_to_db
)

from .discounts_prices_db import (
    upsert_prices_to_db,
    sync_discounts_prices_to_db,
    get_price_changes_report
)

__all__ = [
    'upsert_cards_to_db',
    'sync_content_cards_to_db',
    'upsert_prices_to_db',
    'sync_discounts_prices_to_db',
    'get_price_changes_report'
]

