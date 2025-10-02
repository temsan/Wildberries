"""
Клиент для метода Wildberries Statistics API: /api/v1/supplier/stocks

Документация (кратко):
- Эндпоинт: https://statistics-api.wildberries.ru/api/v1/supplier/stocks
- Хедер: Authorization: <API_KEY>
- Параметр: dateFrom (RFC3339, МСК, например: 2019-06-20 или 2019-06-20T00:00:00)
- Пагинация: используйте lastChangeDate из последней записи предыдущего ответа
- Остановка: пустой ответ []
- Лимит: 1 запрос/мин на аккаунт. В коде предусмотрено опциональное троттлинг-ожидание
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional

import importlib.util
import requests


# Импорт API ключа так же, как в других модулях проекта
BASE_DIR = Path(__file__).resolve().parents[1]
api_keys_path = BASE_DIR / "api_keys.py"
spec = importlib.util.spec_from_file_location("api_keys", str(api_keys_path))
api_keys_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(api_keys_module)
API_KEY: str = api_keys_module.WB_API_TOKEN


class WildberriesSupplierStocksAPI:
    """Клиент для получения остатков по складам WB через Statistics API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://statistics-api.wildberries.ru/api/v1/supplier/stocks"
        self.headers = {"Authorization": api_key}

    def fetch_stocks_page(self, date_from: str) -> List[Dict]:
        """Выполняет один запрос к /supplier/stocks.

        Args:
            date_from: Значение параметра dateFrom (RFC3339, Московское время)

        Returns:
            Список записей остатков. Пустой список означает, что данных больше нет.
        """
        params = {"dateFrom": date_from}
        response = requests.get(self.base_url, headers=self.headers, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise ValueError("Ожидался список записей в ответе Statistics API")
        return data

    def iterate_all_stocks(
        self,
        start_date_from: str,
        *,
        throttle: bool = True,
        throttle_seconds: int = 61,
        max_pages: Optional[int] = None,
    ) -> Iterator[Dict]:
        """Итерирует все записи остатков, следуя правилам пагинации по lastChangeDate.

        Args:
            start_date_from: Начальное значение dateFrom (RFC3339)
            throttle: Включить ожидание между запросами для соблюдения лимита
            throttle_seconds: Количество секунд ожидания между запросами
            max_pages: Опционально ограничивает число страниц (для тестов)

        Yields:
            Объекты записей остатков.
        """
        current_date_from = start_date_from
        page_index = 0

        while True:
            if max_pages is not None and page_index >= max_pages:
                break

            page = self.fetch_stocks_page(current_date_from)
            if not page:
                break

            for record in page:
                yield record

            last_change = page[-1].get("lastChangeDate")
            if not last_change:
                # Если по какой-то причине поле отсутствует, прекращаем чтобы не зациклиться
                break

            current_date_from = last_change
            page_index += 1

            if throttle:
                time.sleep(throttle_seconds)

    def fetch_all_stocks(
        self,
        start_date_from: str,
        *,
        throttle: bool = True,
        throttle_seconds: int = 61,
        max_pages: Optional[int] = None,
    ) -> List[Dict]:
        """Собирает все записи остатков в список.

        Для больших объёмов данных используйте генератор iterate_all_stocks, чтобы не
        хранить всё в памяти.
        """
        return list(
            self.iterate_all_stocks(
                start_date_from,
                throttle=throttle,
                throttle_seconds=throttle_seconds,
                max_pages=max_pages,
            )
        )


def _example_run() -> None:
    """Пример использования: получает первую страницу для быстрой проверки."""
    api = WildberriesSupplierStocksAPI(API_KEY)
    # Укажите максимально раннюю дату, если требуется полный остаток
    date_from = "2019-06-20"
    first_page = api.fetch_stocks_page(date_from)
    print(f"Получено записей: {len(first_page)}")
    if first_page:
        print("Пример записи:")
        sample = first_page[0]
        for key in [
            "lastChangeDate",
            "warehouseName",
            "supplierArticle",
            "nmId",
            "barcode",
            "quantity",
            "quantityFull",
        ]:
            if key in sample:
                print(f"  {key}: {sample[key]}")


if __name__ == "__main__":
    _example_run()


