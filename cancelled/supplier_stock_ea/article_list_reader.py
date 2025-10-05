"""
Функция для чтения списка артикулов из Google Sheets (supplier_stock проект).

Поведение аналогично warehouse_remains_ea/article_list_reader.py
"""

import importlib.util
from pathlib import Path
from typing import List


# Импортируем GOOGLE_CREDENTIALS_FILE из api_keys.py (динамически)
BASE_DIR = Path(__file__).resolve().parents[2]
api_keys_path = BASE_DIR / 'api_keys.py'
spec = importlib.util.spec_from_file_location("api_keys", str(api_keys_path))
api_keys_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_keys_module)
GOOGLE_CREDENTIALS_FILE = api_keys_module.GOOGLE_CREDENTIALS_FILE


def get_article_list_from_google_sheets(sheet_url: str, sheet_name: str, cell_range: str) -> List[str]:
    """Читает список артикулов из Google Sheets по указанному листу и диапазону."""
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=scopes)
        service = build('sheets', 'v4', credentials=credentials)

        sheet_id = extract_sheet_id(sheet_url)
        if not sheet_id:
            print("❌ Не удалось извлечь ID таблицы из URL")
            return []

        range_name = f"{sheet_name}!{cell_range}"
        result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=range_name).execute()
        values = result.get('values', [])

        flat: List[str] = []
        for row in values:
            for cell in row:
                text = str(cell).strip()
                if text:
                    flat.append(text)

        print(f"✅ Прочитано {len(flat)} артикулов из Google Sheets")
        return flat

    except Exception as exc:
        print(f"❌ Ошибка при чтении Google Sheets: {exc}")
        return []


def extract_sheet_id(sheet_url: str) -> str:
    """Извлекает ID Google Sheets из URL формата https://docs.google.com/spreadsheets/d/<ID>/..."""
    try:
        marker = '/spreadsheets/d/'
        if marker in sheet_url:
            start = sheet_url.find(marker) + len(marker)
            end = sheet_url.find('/', start)
            if end == -1:
                end = len(sheet_url)
            return sheet_url[start:end]
        return ""
    except Exception:
        return ""


