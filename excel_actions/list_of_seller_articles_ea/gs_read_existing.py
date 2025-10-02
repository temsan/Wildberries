"""
Чтение существующих строк из Google Sheets для базы артикулов.
Ожидается порядок колонок: nmId | barcode | supplierArticle | size (названия могут отличаться).
"""

from __future__ import annotations

from typing import List, Tuple
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


def read_existing_keys(spreadsheet_id: str, sheet_name: str, start_row: int = 2) -> List[Tuple[int, str, str, str]]:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    if GOOGLE_CREDENTIALS_INFO:
        credentials = Credentials.from_service_account_info(GOOGLE_CREDENTIALS_INFO, scopes=scopes)
    else:
        credentials = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=scopes)
    service = build('sheets', 'v4', credentials=credentials)

    # Считываем строку заголовков и определяем индексы всех алиасов
    hdr_rng = f"{sheet_name}!1:1"
    hdr_res = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=hdr_rng).execute()
    headers = hdr_res.get('values', [[]])
    headers = headers[0] if headers else []

    def _norm(s: str) -> str:
        return " ".join(str(s).strip().lower().split()) if s is not None else ""

    name_to_indices = {
        'article': [],
        'barcode': [],
        'vendor': [],
        'size': [],
    }
    for idx0, title in enumerate(headers):
        t = _norm(title)
        for kind, aliases in lsa_cfg.ALIASES.items():
            if _norm(t) in {_norm(a) for a in aliases}:
                if kind in name_to_indices:
                    name_to_indices[kind].append(idx0)
    # Для чтения берём первую найденную колонку по каждому виду, предупреждаем если нет
    missing = [k for k, v in name_to_indices.items() if not v]
    if missing:
        print(f"⚠️ Отсутствуют колонки: {', '.join(missing)}")
    # Получаем данные по первым найденным колонкам
    cols_order = []
    for k in ('article', 'barcode', 'vendor', 'size'):
        if name_to_indices[k]:
            col_letter = _col_index_to_label(name_to_indices[k][0] + 1)
            cols_order.append(f"{sheet_name}!{col_letter}{start_row}:{col_letter}")
        else:
            cols_order.append(None)
    # batch get для существующих колонок
    ranges = [r for r in cols_order if r]
    vrs = []
    if ranges:
        batch = service.spreadsheets().values().batchGet(spreadsheetId=spreadsheet_id, ranges=ranges).execute()
        vrs = batch.get('valueRanges', [])
    # Собираем значения в единую матрицу article, barcode, vendor, size
    # Вставляем пустые столбцы, если какие-то отсутствуют
    cols = []
    vr_iter = iter(vrs)
    for r in cols_order:
        if r is None:
            cols.append([])
        else:
            cols.append(next(vr_iter, {}).get('values', []))
    max_len = max((len(c) for c in cols), default=0)
    values = []
    for i in range(max_len):
        row = []
        for c in cols:
            row.append(c[i][0] if i < len(c) and c[i] else '')
        values.append(row)

    out: List[Tuple[int, str, str, str]] = []
    for row in values:
        nm = int(row[0]) if len(row) > 0 and str(row[0]).strip() else None
        bc = str(row[1]).strip() if len(row) > 1 else ""
        sa = str(row[2]).strip() if len(row) > 2 else ""
        size = str(row[3]).strip() if len(row) > 3 else ""
        if nm is None:
            continue
        out.append((nm, bc, sa, size))
    return out


