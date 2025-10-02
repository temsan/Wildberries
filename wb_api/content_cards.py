"""
Client for WB Content API: /content/v2/get/cards/list

POST https://content-api.wildberries.ru/content/v2/get/cards/list
Auth: Authorization header (token with Content/Promotion category)

Minimal test run when executed as a script: fetch first page and print brief info.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import importlib.util
import requests


# Load API key from api_keys.py (same pattern as other modules)
BASE_DIR = Path(__file__).resolve().parents[1]
api_keys_path = BASE_DIR / "api_keys.py"
spec = importlib.util.spec_from_file_location("api_keys", str(api_keys_path))
api_keys_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(api_keys_module)
API_KEY: str = api_keys_module.WB_API_TOKEN


class WBContentCardsClient:
    """Client for listing product cards via Content API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://content-api.wildberries.ru/content/v2/get/cards/list"
        self.headers = {"Authorization": api_key, "Content-Type": "application/json"}

    def fetch_cards_page(
        self,
        *,
        limit: int = 100,
        with_photo: int = -1,
        locale: Optional[str] = "ru",
        cursor_updated_at: Optional[str] = None,
        cursor_nm_id: Optional[int] = None,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """Fetch one page of cards. Returns raw JSON dict.

        with_photo: -1 (all), 0 (without), 1 (with)
        """
        body: Dict[str, Any] = {
            "settings": {
                "cursor": {"limit": limit},
                "filter": {"withPhoto": with_photo},
            }
        }
        if locale:
            body["settings"]["locale"] = locale
        if cursor_updated_at is not None:
            body["settings"]["cursor"]["updatedAt"] = cursor_updated_at
        if cursor_nm_id is not None:
            body["settings"]["cursor"]["nmID"] = cursor_nm_id

        resp = requests.post(self.base_url, headers=self.headers, json=body, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def iterate_all_cards(
        self,
        *,
        limit: int = 100,
        with_photo: int = -1,
        locale: Optional[str] = "ru",
        sleep_seconds: float = 0.7,
        max_pages: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch multiple pages using cursor until total < limit or no cards.

        Returns a flat list of cards (concatenated).
        """
        all_cards: List[Dict[str, Any]] = []
        updated_at: Optional[str] = None
        nm_id: Optional[int] = None
        page_count = 0

        while True:
            if max_pages is not None and page_count >= max_pages:
                break

            data = self.fetch_cards_page(
                limit=limit,
                with_photo=with_photo,
                locale=locale,
                cursor_updated_at=updated_at,
                cursor_nm_id=nm_id,
            )
            cards = data.get("cards", []) if isinstance(data, dict) else []
            total = data.get("total") if isinstance(data, dict) else None
            cursor = data.get("cursor") if isinstance(data, dict) else None

            if not isinstance(cards, list) or not cards:
                break

            all_cards.extend(cards)
            page_count += 1

            # Prepare next cursor
            if isinstance(cursor, dict):
                updated_at = cursor.get("updatedAt")
                nm_id = cursor.get("nmID")
            else:
                updated_at = None
                nm_id = None

            # Stop if total hints the end
            if isinstance(total, int) and total < limit:
                break

            time.sleep(sleep_seconds)

        return all_cards


def _mask(value: Optional[str]) -> str:
    if not value:
        return "<empty>"
    v = str(value)
    return (v[:12] + "..." + v[-12:]) if len(v) > 24 else "***"


def _example_run() -> None:
    client = WBContentCardsClient(API_KEY)
    print(f"Endpoint: {client.base_url}")
    print(f"API key (masked): {_mask(API_KEY)}")

    try:
        data = client.fetch_cards_page(limit=100, with_photo=-1, locale="ru")
    except requests.HTTPError as e:
        print("HTTP error:", e)
        if e.response is not None:
            print("Response:", e.response.text[:500])
        return
    except Exception as e:
        print("Error:", type(e).__name__, str(e)[:500])
        return

    cards = data.get("cards", []) if isinstance(data, dict) else []
    total = data.get("total") if isinstance(data, dict) else None
    cursor = data.get("cursor") if isinstance(data, dict) else None

    print(f"cards count (this page): {len(cards)}; total: {total}")
    if isinstance(cursor, dict):
        print("cursor:", {k: cursor.get(k) for k in ("updatedAt", "nmID")})
    if cards:
        sample = cards[0]
        print("sample keys:", sorted(sample.keys()))


if __name__ == "__main__":
    _example_run()


