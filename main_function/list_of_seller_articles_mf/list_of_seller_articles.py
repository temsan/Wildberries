"""
Main: сбор базы артикулов из Content API (cards list) и upsert в Google Sheets.

Поля: nmID | barcode (из sizes[].skus) | vendorCode | size
Уникальность по четверке. Если совпали (nmID, barcode), но vendorCode или size изменился — обновляем на месте.
Новые строки добавляем в конец и красим светло‑серым.
Дополнительно записываем уникальные пары (vendorCode, nmID) в столбцы H и I.
"""

from __future__ import annotations

from pathlib import Path
import importlib.util


BASE_DIR = Path(__file__).resolve().parents[2]

# Импорт API для Content (cards list)
content_api_path = BASE_DIR / 'wb_api' / 'content_cards.py'
spec = importlib.util.spec_from_file_location('content_cards', str(content_api_path))
content_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(content_mod)
WBContentCardsClient = content_mod.WBContentCardsClient

# Ключи/константы
api_keys_path = BASE_DIR / 'api_keys.py'
spec_keys = importlib.util.spec_from_file_location('api_keys', str(api_keys_path))
ak = importlib.util.module_from_spec(spec_keys)
spec_keys.loader.exec_module(ak)
API_KEY = ak.WB_API_TOKEN
SHEET_ID = ak.GOOGLE_SHEET_ID_ARTICLES

# Нормализация
norm_path = BASE_DIR / 'excel_actions' / 'list_of_seller_articles_ea' / 'normalize_articles.py'
spec_norm = importlib.util.spec_from_file_location('normalize_articles', str(norm_path))
norm = importlib.util.module_from_spec(spec_norm)
spec_norm.loader.exec_module(norm)
extract_triples_from_content_cards = norm.extract_triples_from_content_cards

# Google Sheets read/upsert
gs_read_path = BASE_DIR / 'excel_actions' / 'list_of_seller_articles_ea' / 'gs_read_existing.py'
spec_read = importlib.util.spec_from_file_location('gs_read_existing', str(gs_read_path))
gs_read = importlib.util.module_from_spec(spec_read)
spec_read.loader.exec_module(gs_read)
read_existing_keys = gs_read.read_existing_keys

gs_upsert_path = BASE_DIR / 'excel_actions' / 'list_of_seller_articles_ea' / 'gs_upsert_append.py'
spec_upsert = importlib.util.spec_from_file_location('gs_upsert_append', str(gs_upsert_path))
gs_upsert = importlib.util.module_from_spec(spec_upsert)
spec_upsert.loader.exec_module(gs_upsert)
upsert_articles = gs_upsert.upsert_articles

# ========================================
# 🔧 ИСКЛЮЧЕНИЯ (НАСТРОЙКИ В МЕЙНЕ)
# ========================================
# Укажите nmID, которые НЕ НУЖНО добавлять/обновлять в базе артикулов.
# Тройки (nmID, barcode, vendorCode) с этими nmID будут проигнорированы.
EXCLUDED_NM_IDS = {}
    # Пример: 12345678

# Structure validator (strict top-level) via dynamic import
struct_path = BASE_DIR / 'excel_actions' / 'list_of_seller_articles_ea' / 'structure_validator.py'
spec_struct = importlib.util.spec_from_file_location('articles_structure_validator', str(struct_path))
articles_struct = importlib.util.module_from_spec(spec_struct)
spec_struct.loader.exec_module(articles_struct)
articles_check_and_validate_structure = articles_struct.check_and_validate_structure


def main() -> None:
    print("🚀 Старт сборки базы артикулов (Content API)")
    client = WBContentCardsClient(API_KEY)
    # Диагностика: показать, какой API и какой ключ используются (замаскированно)
    def _mask(v: str) -> str:
        if not v:
            return "<empty>"
        return (v[:12] + "..." + v[-12:]) if len(v) > 24 else "***"
    print(f"Using API endpoint: {client.base_url}")
    print(f"Using API key (masked): {_mask(API_KEY)}")

# 1) Получаем карточки (первая страница)
    #data = client.fetch_cards_page(limit=100, with_photo=-1, locale="ru")
    #rows = data.get('cards', []) if isinstance(data, dict) else []

    # 1) Получаем все карточки (с пагинацией)
    rows = client.iterate_all_cards(limit=100, with_photo=-1, locale="ru")

    # Проверка структуры по нашему строгому валидатору
    if not articles_check_and_validate_structure(rows):
        print("🛑 Выполнение остановлено из-за несоответствия структуры")
        return
    if not rows:
        print("⚠️ Пустой список cards")
        return

    # 3) Нормализация уникальных четверок и пар
    items, vendor_nmid_pairs = extract_triples_from_content_cards(rows)
    if EXCLUDED_NM_IDS:
        before = len(items)
        items = [t for t in items if t[0] not in EXCLUDED_NM_IDS]
        vendor_nmid_pairs = [p for p in vendor_nmid_pairs if p[1] not in EXCLUDED_NM_IDS]
        after = len(items)
        print(f"Исключения nmID: {len(EXCLUDED_NM_IDS)}; отфильтровано {before - after} четверок")
    print(f"Найдено уникальных четверок: {len(items)} (nmID, barcode, vendorCode, size)")
    print(f"Найдено уникальных пар: {len(vendor_nmid_pairs)} (vendorCode, nmID)")

    # 4) Читать существующие ключи из Google Sheets
    sheet_name = "База артикулов"
    start_row = 2
    existing = read_existing_keys(SHEET_ID, sheet_name, start_row=start_row)
    print(f"Прочитано существующих строк: {len(existing)}")

    # 5) Upsert: обновить supplierArticle по (nmId, barcode); новые добавить в конец и покрасить
    # Также записываем уникальные пары (vendorCode, nmID) в столбцы H и I
    upsert_articles(SHEET_ID, sheet_name, start_row, existing, items)
    print("✅ Готово: обновления применены, новые строки добавлены, пары vendorCode-nmID записаны.")


if __name__ == "__main__":
    main()


