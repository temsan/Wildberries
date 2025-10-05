"""
Google Sheets writer for supplier_stock.

Two public functions:
1) clear_target_cells(...): clears cells under specified warehouse and total columns
   for all rows where column D has a non-empty value (first occurrence strategy assumed).
2) write_per_warehouse_and_totals(...): writes per-warehouse quantity and in-way totals
   into designated columns based on header row mapping. Also reports warehouses that
   appear in API data but are missing in the sheet header.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple
from pathlib import Path
import importlib.util


# Import Google credentials path
BASE_DIR = Path(__file__).resolve().parents[2]
api_keys_path = BASE_DIR / 'api_keys.py'
spec = importlib.util.spec_from_file_location("api_keys", str(api_keys_path))
api_keys_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_keys_module)
GOOGLE_CREDENTIALS_FILE = api_keys_module.GOOGLE_CREDENTIALS_FILE


def _get_service():
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=scopes)
    return build('sheets', 'v4', credentials=credentials)


def _col_index_to_label(index_1based: int) -> str:
    label = ""
    n = index_1based
    while n > 0:
        n, rem = divmod(n - 1, 26)
        label = chr(65 + rem) + label
    return label


def _parse_start_col(header_range: str) -> int:
    # e.g., "A1:CA1" -> start col A -> 1
    start = header_range.split(':')[0]
    col_letters = ''.join(c for c in start if c.isalpha())
    # convert letters to 1-based index
    idx = 0
    for ch in col_letters:
        idx = idx * 26 + (ord(ch.upper()) - 64)
    return idx


def _build_header_map(service, spreadsheet_id: str, sheet_name: str, header_range: str) -> Dict[str, str]:
    rng = f"{sheet_name}!{header_range}"
    res = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=rng).execute()
    values = res.get('values', [[]])
    row = values[0] if values else []

    start_col = _parse_start_col(header_range)
    header_map: Dict[str, str] = {}
    for i, title in enumerate(row):
        title_norm = str(title).strip()
        if not title_norm:
            continue
        col_label = _col_index_to_label(start_col + i)
        header_map[title_norm] = col_label
    return header_map


def _build_barcode_row_map(service, spreadsheet_id: str, sheet_name: str, article_col: str, start_row: int, prefer_first: bool = True) -> Dict[str, int]:
    rng = f"{sheet_name}!{article_col}{start_row}:{article_col}"
    res = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=rng).execute()
    values = res.get('values', [])
    barcode_to_row: Dict[str, int] = {}
    if not values:
        return barcode_to_row
    for offset, row_vals in enumerate(values, start=0):
        # row_vals is a list for the single column, may be empty
        cell = row_vals[0].strip() if row_vals else ""
        if not cell:
            continue
        row_num = start_row + offset
        key = str(cell)
        if prefer_first:
            if key not in barcode_to_row:
                barcode_to_row[key] = row_num
        else:
            barcode_to_row[key] = row_num
    return barcode_to_row


def _api_warehouses_from_rows(per_warehouse_rows: Iterable[Dict[str, Any]]) -> List[str]:
    seen = set()
    out = []
    for r in per_warehouse_rows:
        wh = str(r.get('warehouseName', '')).strip()
        if wh and wh not in seen:
            seen.add(wh)
            out.append(wh)
    return out


def clear_target_cells(
    spreadsheet_id: str,
    sheet_name: str,
    header_range: str,
    article_col: str,
    start_row: int,
    warehouses_expected: List[str],
    total_to_client_header: str,
    total_from_client_header: str,
    allowed_nm_ids: set[str] | None = None,
) -> None:
    """Clears cells under given warehouse and total columns for rows with non-empty D.

    Only rows with non-empty article in column D are cleared.
    """
    service = _get_service()
    header_map = _build_header_map(service, spreadsheet_id, sheet_name, header_range)

    # Build list of column letters to clear
    col_letters: List[str] = []
    missing_headers: List[str] = []
    for title in warehouses_expected + [total_to_client_header, total_from_client_header]:
        if title in header_map:
            col_letters.append(header_map[title])
        else:
            missing_headers.append(title)
    if missing_headers:
        print(f"⚠️ В шапке не найдены столбцы: {missing_headers}")

    # Determine rows to clear: rows where column C has a value
    barcode_map = _build_barcode_row_map(service, spreadsheet_id, sheet_name, article_col, start_row, prefer_first=True)
    if allowed_nm_ids is not None:
        allowed = {str(x).strip() for x in allowed_nm_ids if str(x).strip()}
        rows_to_clear = sorted(row for barcode, row in barcode_map.items() if barcode in allowed)
    else:
        rows_to_clear = sorted(barcode_map.values())
    if not rows_to_clear or not col_letters:
        print("ℹ️ Нет строк или столбцов для очистки.")
        return

    # Build ranges to clear
    ranges = [f"{sheet_name}!{col}{row}:{col}{row}" for row in rows_to_clear for col in col_letters]

    body = {"ranges": ranges}
    service.spreadsheets().values().batchClear(spreadsheetId=spreadsheet_id, body=body).execute()
    print(f"✅ Очищено ячеек: {len(ranges)}")


def write_per_warehouse_and_totals(
    spreadsheet_id: str,
    sheet_name: str,
    header_range: str,
    article_col: str,
    start_row: int,
    warehouses_expected: List[str],
    total_to_client_header: str,
    total_from_client_header: str,
    per_warehouse_rows: List[Dict[str, Any]],
    inway_totals_rows: List[Dict[str, Any]],
) -> List[str]:
    """Writes per-warehouse quantities and totals. Returns list of warehouses missing in header.

    Also prints warehouses present in API but absent in the provided expected list (header).
    """
    service = _get_service()
    header_map = _build_header_map(service, spreadsheet_id, sheet_name, header_range)
    barcode_row_map = _build_barcode_row_map(service, spreadsheet_id, sheet_name, article_col, start_row, prefer_first=True)

    # Missing warehouses check (API vs expected/header)
    api_warehouses = set(_api_warehouses_from_rows(per_warehouse_rows))
    header_warehouses = set(warehouses_expected)
    missing_in_header = sorted(api_warehouses - header_warehouses)
    if missing_in_header:
        print(f"⚠️ В API найдены склады, отсутствующие в шапке: {missing_in_header}")

    # Build writes for per-warehouse quantities
    value_ranges: List[Dict[str, Any]] = []
    for r in per_warehouse_rows:
        barcode = str(r.get('barcode', ''))
        wh = str(r.get('warehouseName', '')).strip()
        if not barcode or wh not in header_map or barcode not in barcode_row_map:
            continue
        row_num = barcode_row_map[barcode]
        col = header_map[wh]
        rng = f"{sheet_name}!{col}{row_num}:{col}{row_num}"
        value_ranges.append({"range": rng, "values": [[int(r.get('quantity', 0) or 0)]]})

    # Build writes for totals (in-way)
    totals_by_barcode: Dict[str, Dict[str, int]] = {}
    for t in inway_totals_rows:
        barcode = str(t.get('barcode', ''))
        if not barcode:
            continue
        totals_by_barcode[barcode] = {
            'to': int(t.get('inWayToClientTotal', 0) or 0),
            'from': int(t.get('inWayFromClientTotal', 0) or 0),
        }

    col_to = header_map.get(total_to_client_header)
    col_from = header_map.get(total_from_client_header)
    for barcode, totals in totals_by_barcode.items():
        row_num = barcode_row_map.get(barcode)
        if not row_num:
            continue
        if col_to:
            rng_to = f"{sheet_name}!{col_to}{row_num}:{col_to}{row_num}"
            value_ranges.append({"range": rng_to, "values": [[totals['to']]]})
        if col_from:
            rng_from = f"{sheet_name}!{col_from}{row_num}:{col_from}{row_num}"
            value_ranges.append({"range": rng_from, "values": [[totals['from']]]})

    if not value_ranges:
        print("ℹ️ Нет данных для записи.")
        return missing_in_header

    body = {"valueInputOption": "RAW", "data": value_ranges}
    service.spreadsheets().values().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
    print(f"✅ Записано ячеек: {len(value_ranges)}")
    return missing_in_header


