"""
Добавление новых строк и апдейт supplierArticle по ключу (nmId, barcode) в Google Sheets.
Новые строки окрашиваются светло‑серым цветом.
"""

from __future__ import annotations

from typing import Iterable, Tuple, List
from pathlib import Path
import importlib.util


BASE_DIR = Path(__file__).resolve().parents[2]
api_keys_path = BASE_DIR / 'api_keys.py'
spec = importlib.util.spec_from_file_location("api_keys", str(api_keys_path))
api_keys_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_keys_module)
GOOGLE_CREDENTIALS_FILE = getattr(api_keys_module, 'GOOGLE_CREDENTIALS_FILE', '')
GOOGLE_CREDENTIALS_INFO = getattr(api_keys_module, 'GOOGLE_CREDENTIALS_INFO', None)

alias_cfg_path = Path(__file__).resolve().with_name('header_config.py')
spec_cfg = importlib.util.spec_from_file_location('lsa_header_config', str(alias_cfg_path))
lsa_cfg = importlib.util.module_from_spec(spec_cfg)
spec_cfg.loader.exec_module(lsa_cfg)


def _col_index_to_label(index_1based: int) -> str:
    label = ""
    n = index_1based
    while n > 0:
        n, rem = divmod(n - 1, 26)
        label = chr(65 + rem) + label
    return label


def _norm(s: str) -> str:
    return " ".join(str(s).strip().lower().split()) if s is not None else ""


def _scan_header_indices(service, spreadsheet_id: str, sheet_name: str) -> dict[str, list[int]]:
    """Возвращает индексы (0-based) всех колонок по алиасам для article, barcode, vendor, size."""
    rng = f"{sheet_name}!1:1"
    res = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=rng).execute()
    headers = res.get('values', [[]])
    headers = headers[0] if headers else []
    name_to_indices: dict[str, list[int]] = {k: [] for k in ('article', 'barcode', 'vendor', 'size')}
    alias_map = lsa_cfg.ALIASES
    for idx0, title in enumerate(headers):
        t_norm = _norm(title)
        for kind, aliases in alias_map.items():
            if t_norm in {_norm(a) for a in aliases}:
                if kind in name_to_indices:
                    name_to_indices[kind].append(idx0)
    # Предупреждение о пропущенных
    missing = [k for k, v in name_to_indices.items() if not v]
    if missing:
        print(f"⚠️ Отсутствуют колонки для записи: {', '.join(missing)}")
    return name_to_indices


def upsert_articles(
    spreadsheet_id: str,
    sheet_name: str,
    start_row: int,
    existing: List[Tuple[int, str, str, str]],
    new_items: Iterable[Tuple[int, str, str, str]],
) -> None:
    """Обновляет supplierArticle по совпадению (nmId, barcode) и добавляет новые строки в конец.
    Также записывает уникальные пары (vendorCode, nmID) в столбцы H и I.
    """
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    if GOOGLE_CREDENTIALS_INFO:
        credentials = Credentials.from_service_account_info(GOOGLE_CREDENTIALS_INFO, scopes=scopes)
    else:
        credentials = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=scopes)
    service = build('sheets', 'v4', credentials=credentials)

    # Индексы существующих по ключу (nmId, barcode) -> (row_index, supplierArticle, size)
    index = {}
    for i, (nm, bc, sa, size) in enumerate(existing, start=start_row):
        index[(nm, bc)] = (i, sa, size)

    updates = []  # (row, new_sa, new_size)
    to_append: List[Tuple[int, str, str, str]] = []

    for nm, bc, sa, size in new_items:
        key = (nm, bc)
        if key in index:
            row_idx, old_sa, old_size = index[key]
            if (sa and sa != old_sa) or (size and size != old_size):
                updates.append((row_idx, sa, size))
        else:
            to_append.append((nm, bc, sa, size))

    # Выполняем апдейты supplierArticle и size, мультизапись во все найденные колонки-алиасы
    if updates:
        data = []
        name_to_indices = _scan_header_indices(service, spreadsheet_id, sheet_name)
        vendor_cols = [ _col_index_to_label(i+1) for i in name_to_indices['vendor'] ]
        size_cols = [ _col_index_to_label(i+1) for i in name_to_indices['size'] ]
        for row_idx, new_sa, new_size in updates:
            for col in vendor_cols:
                rng_v = f"{sheet_name}!{col}{row_idx}:{col}{row_idx}"
                data.append({"range": rng_v, "values": [[new_sa]]})
            for col in size_cols:
                rng_s = f"{sheet_name}!{col}{row_idx}:{col}{row_idx}"
                data.append({"range": rng_s, "values": [[new_size]]})
        body = {"valueInputOption": "RAW", "data": data}
        service.spreadsheets().values().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

    # Добавляем новые строки в конец и красим их
    if to_append:
        # Определяем целевые колонки по алиасам
        name_to_indices = _scan_header_indices(service, spreadsheet_id, sheet_name)
        article_cols = [ _col_index_to_label(i+1) for i in name_to_indices['article'] ]
        bc_cols = [ _col_index_to_label(i+1) for i in name_to_indices['barcode'] ]
        vendor_cols = [ _col_index_to_label(i+1) for i in name_to_indices['vendor'] ]
        size_cols = [ _col_index_to_label(i+1) for i in name_to_indices['size'] ]

        # Последняя занятая строка: берём максимум среди всех целевых колонок
        def _col_last_row(letter: str) -> int:
            rng = f"{sheet_name}!{letter}:{letter}"
            r = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=rng).execute()
            vals = r.get('values', [])
            return len(vals)

        target_letters = list(set(article_cols + bc_cols + vendor_cols + size_cols))
        last_row_candidates = [_col_last_row(c) for c in target_letters] or [0]
        last_row = max(last_row_candidates)
        start = max(start_row, last_row + 1)

        # Запись значений (четверки), динамически по найденным колонкам
        value_ranges = []
        for offset, (nm, bc, sa, size) in enumerate(to_append):
            row = start + offset
            for col in article_cols:
                value_ranges.append({"range": f"{sheet_name}!{col}{row}:{col}{row}", "values": [[nm]]})
            for col in bc_cols:
                value_ranges.append({"range": f"{sheet_name}!{col}{row}:{col}{row}", "values": [[bc]]})
            for col in vendor_cols:
                value_ranges.append({"range": f"{sheet_name}!{col}{row}:{col}{row}", "values": [[sa]]})
            for col in size_cols:
                value_ranges.append({"range": f"{sheet_name}!{col}{row}:{col}{row}", "values": [[size]]})
        if value_ranges:
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"valueInputOption": "RAW", "data": value_ranges}
            ).execute()

        # Для окраски вычисляем end
        end = start + len(to_append) - 1

        # Окраска светло‑серым (RGB 0.9333) только по реально использованным колонкам
        def _col_letters_to_index(col_letters: str) -> int:
            idx = 0
            for ch in col_letters:
                idx = idx * 26 + (ord(ch.upper()) - 64)
            return idx - 1  # zero-based

        used_letters = sorted(set(article_cols + bc_cols + vendor_cols + size_cols))
        if used_letters:
            sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheet_id = next(s['properties']['sheetId'] for s in sheet_metadata['sheets'] if s['properties']['title'] == sheet_name)
            requests = []
            for letter in used_letters:
                c_idx = _col_letters_to_index(letter)
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start - 1,
                            "endRowIndex": end,
                            "startColumnIndex": c_idx,
                            "endColumnIndex": c_idx + 1,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {"red": 0.9333, "green": 0.9333, "blue": 0.9333}
                            }
                        },
                        "fields": "userEnteredFormat.backgroundColor",
                    }
                })
            if requests:
                service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests}).execute()

    # Блок записи пар (vendorCode, nmID) в H:I удалён по требованиям


