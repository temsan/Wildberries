"""
Утилита для записи отметки времени последнего обновления в Google Sheets.

Функция write_last_updated пишет текущие дату и время в указанную ячейку
(по умолчанию A1) на заданном листе.
"""

from datetime import datetime
from pathlib import Path
import importlib.util


# Импорт путей/ключей
BASE_DIR = Path(__file__).resolve().parents[2]
api_keys_path = BASE_DIR / 'api_keys.py'
spec = importlib.util.spec_from_file_location("api_keys", str(api_keys_path))
api_keys_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_keys_module)
GOOGLE_CREDENTIALS_FILE = getattr(api_keys_module, 'GOOGLE_CREDENTIALS_FILE', '')
GOOGLE_CREDENTIALS_INFO = getattr(api_keys_module, 'GOOGLE_CREDENTIALS_INFO', None)


def _get_service():
    """Создаёт клиент Google Sheets API."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    if GOOGLE_CREDENTIALS_INFO:
        credentials = Credentials.from_service_account_info(GOOGLE_CREDENTIALS_INFO, scopes=scopes)
    else:
        credentials = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=scopes)
    return build('sheets', 'v4', credentials=credentials)


def write_last_updated(
    spreadsheet_id: str,
    sheet_name: str,
    cell: str = "A1",
    prefix: str = "Обновлено: ",
    dt_fmt: str = "%Y-%m-%d %H:%M:%S",
) -> None:
    """
    Записывает отметку времени последнего обновления в указанную ячейку.

    Args:
        spreadsheet_id: ID Google Таблицы
        sheet_name: Имя листа, например "Остатки по складам"
        cell: Ячейка для записи (по умолчанию "A1")
        prefix: Префикс перед датой/временем (по умолчанию "Обновлено: ")
        dt_fmt: Формат даты/времени strftime (по умолчанию YYYY-MM-DD HH:MM:SS)
    """

    service = _get_service()

    # Формируем человекочитаемую метку времени (локальная зона системы)
    now_str = datetime.now().strftime(dt_fmt)
    value = f"{prefix}{now_str}"

    # Диапазон вида: 'Лист'!A1
    sheet_ref = f"'{sheet_name}'" if ' ' in sheet_name else sheet_name
    rng = f"{sheet_ref}!{cell}:{cell}"

    body = {
        "valueInputOption": "RAW",
        "data": [
            {"range": rng, "values": [[value]]}
        ],
    }

    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=body,
    ).execute()


