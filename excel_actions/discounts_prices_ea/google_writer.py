"""
Google Sheets writer for discounts_prices data.

Функция для записи обработанных данных discounts_prices в Google таблицу
с настраиваемыми параметрами листа и диапазона поиска артикулов.

ПОРЯДОК СТОЛБЦОВ ДЛЯ ЗАПИСИ:
1. prices - базовая цена
2. discount - скидка в процентах  
3. discountedPrices - цена со скидкой
4. discountOnSite - дополнительная скидка на сайте
5. priceafterSPP - цена после СПП
6. competitivePrice - конкурентная цена
7. isCompetitivePrice - флаг конкурентной цены (True/False)
8. hasPromotions - наличие промоакций (True/False)

НАСТРОЙКИ ДИАПАЗОНА ПОИСКА АРТИКУЛОВ:
- article_search_range: Диапазон поиска артикулов (например, "A:A", "A1:A500", "B2:B1000")
- start_row: Начальная строка данных (должна соответствовать первой строке в article_search_range)
- sheet_name: Название листа для записи

ПРИМЕРЫ НАСТРОЙКИ:
- Артикулы в столбце A с 1 по 500 строку: article_search_range="A1:A500", start_row=1
- Артикулы в столбце B с 2 по 1000 строку: article_search_range="B2:B1000", start_row=2
- Артикулы в столбце A (весь столбец): article_search_range="A:A", start_row=1
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import importlib.util
import logging
import sys
import time

logger = logging.getLogger(__name__)

# Import Google credentials path
BASE_DIR = Path(__file__).resolve().parents[2]
api_keys_path = BASE_DIR / 'api_keys.py'
spec = importlib.util.spec_from_file_location("api_keys", str(api_keys_path))
api_keys_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_keys_module)
GOOGLE_CREDENTIALS_FILE = api_keys_module.GOOGLE_CREDENTIALS_FILE
GOOGLE_SHEET_ID_UNIT_ECONOMICS = api_keys_module.GOOGLE_SHEET_ID_UNIT_ECONOMICS
GOOGLE_SHEET_NAME_DISCOUNTS_PRICES = getattr(api_keys_module, "GOOGLE_SHEET_NAME_DISCOUNTS_PRICES", "Юнитка")

# Import header mapping utilities
header_mapping_path = Path(__file__).resolve().parents[1] / 'utils' / 'header_mapping.py'
spec_header = importlib.util.spec_from_file_location("header_mapping", str(header_mapping_path))
header_mapping_module = importlib.util.module_from_spec(spec_header)
sys.modules[spec_header.name] = header_mapping_module
spec_header.loader.exec_module(header_mapping_module)
load_header_map = header_mapping_module.load_header_map
HeaderMappingError = header_mapping_module.HeaderMappingError

# Header configuration (shared constants)
config_path = Path(__file__).resolve().with_name('header_config.py')
spec_config = importlib.util.spec_from_file_location("header_config", str(config_path))
header_config = importlib.util.module_from_spec(spec_config)
spec_config.loader.exec_module(header_config)

HEADER_ROW_INDEX = header_config.HEADER_ROW_INDEX
DISCOUNTS_PRICES_HEADER_ALIASES = header_config.DISCOUNTS_PRICES_HEADER_ALIASES
DATA_COLUMN_KEYS = header_config.DATA_COLUMN_KEYS


def _get_service(credentials_info=None):
    """Получает сервис Google Sheets API."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    scopes = ['https://www.googleapis.com/auth/spreadsheets']

    if credentials_info:
        # Используем переданные credentials
        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
    else:
        # Fallback к старому методу с файлом
        credentials = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=scopes)

    return build('sheets', 'v4', credentials=credentials)


def _get_sheet_id_by_title(service, spreadsheet_id: str, sheet_name: str) -> Optional[int]:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in meta.get('sheets', []):
        props = sheet.get('properties', {})
        if props.get('title') == sheet_name:
            return props.get('sheetId')
    return None


def _get_value_for_key(item: Dict[str, Any], key: str) -> Any:
    """Возвращает значение для записи в зависимости от логического ключа."""

    # Колонки, которые хранятся в таблице в формате процентов
    PERCENT_KEYS = {"discount", "discountOnSite"}

    if key == "prices":
        return item.get("prices", 0)
    if key == "discount":
        # Для процентных колонок Google Sheets ожидает долю (0.3 для 30%)
        value = item.get("discount", 0)
        try:
            return float(value) / 100 if value is not None else 0
        except (ValueError, TypeError):
            return 0
    if key == "discountedPrices":
        return item.get("discountedPrices", 0)
    if key == "discountOnSite":
        value = item.get("discountOnSite", 0)
        try:
            return float(value) / 100 if value is not None else 0
        except (ValueError, TypeError):
            return 0
    if key == "priceafterSPP":
        return item.get("priceafterSPP", 0)
    if key == "competitivePrice":
        return item.get("competitivePrice", 99999)
    if key == "isCompetitivePrice":
        return item.get("isCompetitivePrice", False)
    if key == "hasPromotions":
        return item.get("hasPromotions", False)
    return item.get(key)


def _build_article_row_map(
    service,
    spreadsheet_id: str,
    sheet_name: str,
    header_map,
    start_row: int,
) -> Dict[str, int]:
    """Строит карту артикулов: артикул -> номер строки."""
    rng = header_map.build_column_range("nmID", start_row)
    res = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=rng).execute()
    values = res.get('values', [])
    article_to_row: Dict[str, int] = {}

    if not values:
        return article_to_row

    for offset, row_vals in enumerate(values, start=0):
        cell = row_vals[0].strip() if row_vals else ""
        if not cell:
            continue
        row_num = start_row + offset
        article = str(cell)
        # Используем первое вхождение артикула
        if article not in article_to_row:
            article_to_row[article] = row_num

    return article_to_row


def write_discounts_prices_to_sheet(
    processed_data: List[Dict[str, Any]],
    # ========== НАСТРОЙКИ - ИЗМЕНИТЕ ПРИ НЕОБХОДИМОСТИ ==========
    sheet_name: str = GOOGLE_SHEET_NAME_DISCOUNTS_PRICES,  # Название листа для записи
    article_search_range: str = "A:A",  # Диапазон поиска артикулов (например, "A:A", "A1:A500", "B2:B1000")
    start_row: int = 1,  # Начальная строка данных (должна соответствовать первой строке в article_search_range)
    # ========== НАСТРОЙКИ RATE LIMITING ==========
    requests_per_minute: int = 50,  # Максимум запросов в минуту (оставляем запас)
    delay_between_requests: float = 1.2,  # Задержка между запросами в секундах
    # ============================================
    spreadsheet_id: str = GOOGLE_SHEET_ID_UNIT_ECONOMICS,  # ID Google таблицы (из api_keys.py)
    credentials_info: Dict[str, Any] = None,  # Google credentials (из api_keys.py)
) -> Dict[str, int]:
    """
    Записывает данные discounts_prices в Google таблицу.
    Автоматически определяет столбец с артикулами и вставляет данные в соседние столбцы.
    
    ПЕРЕМЕННЫЕ ДЛЯ НАСТРОЙКИ:
    ========================
    sheet_name (str): Название листа для записи
        - "юнитка" - лист "юнитка" (по умолчанию)
        - "Лист1" - другой лист
        - Любое название листа в таблице
    
    article_search_range (str): Диапазон поиска артикулов
        - "A:A" - весь столбец A (по умолчанию)
        - "A1:A500" - столбец A, строки 1-500
        - "B2:B1000" - столбец B, строки 2-1000
        - "C:C" - весь столбец C
    
    start_row (int): Начальная строка данных
        - 1 - артикулы начинаются с первой строки (по умолчанию)
        - 2 - артикулы начинаются со второй строки (если первая - заголовки)
        - Должна соответствовать первой строке в article_search_range
    
    ПРИМЕРЫ НАСТРОЙКИ:
    =================
    # Артикулы в столбце A с 1 по 500 строку
    article_search_range="A1:A500", start_row=1
    
    # Артикулы в столбце B с 2 по 1000 строку (первая строка - заголовки)
    article_search_range="B2:B1000", start_row=2
    
    # Артикулы в столбце A (весь столбец)
    article_search_range="A:A", start_row=1
    
    Args:
        processed_data: Обработанные данные из data_processor
        sheet_name: Название листа для записи
        article_search_range: Диапазон поиска артикулов
        start_row: Начальная строка данных
        spreadsheet_id: ID Google таблицы
        
    Returns:
        Dict с статистикой: {"processed_rows": int, "not_found_articles": int}
    """
    
    print(f"🔄 Начинаем запись данных в лист '{sheet_name}'...")
    
    service = _get_service(credentials_info)
    
    # === Подготовка header map ===
    header_map = load_header_map(
        service=service,
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name,
        expected_headers=DISCOUNTS_PRICES_HEADER_ALIASES,
        header_row=HEADER_ROW_INDEX,
    )

    # Требуем только наличие столбца артикула, остальные поля — опциональные
    try:
        header_map.get("nmID")
    except HeaderMappingError:
        raise HeaderMappingError("Missing required header: nmID")

    # nmID: колонка с артикулами
    nm_header = header_map.get("nmID")
    print(f"📋 Столбец с артикулами: {nm_header.letter}")

    # Готовим информацию о колонках для записи (только те, что найдены)
    resolved_pairs = [(key, header_map.get_optional(key)) for key in DATA_COLUMN_KEYS]
    column_infos = [(k, info) for k, info in resolved_pairs if info is not None]
    skipped_keys = [k for k, info in resolved_pairs if info is None]
    if skipped_keys:
        logger.info(
            "Пропущены отсутствующие колонки: %s",
            ", ".join(skipped_keys)
        )
    if column_infos:
        logger.info(
            "Найдены колонки для записи: %s",
            ", ".join(f"{k}→{info.letter}" for k, info in column_infos)
        )
    if not column_infos:
        print("ℹ️ Ни одной целевой колонки не найдено. Пропускаем запись значений.")
        column_infos = []
    else:
        start_col_letter = column_infos[0][1].letter
        print(f"📋 Начинаем запись с столбца: {start_col_letter}")

    # Разбиваем колонки на сегменты непрерывных индексов, чтобы писать минимальными диапазонами
    segments: List[List[Tuple[str, Any]]] = []
    current_segment: List[Tuple[str, Any]] = []
    prev_index: Optional[int] = None
    for key, info in column_infos:
        if prev_index is not None and info.index == prev_index + 1:
            current_segment.append((key, info))
        else:
            if current_segment:
                segments.append(current_segment)
            current_segment = [(key, info)]
        prev_index = info.index
    if current_segment:
        segments.append(current_segment)

    # Примечание: определение колонки артикула выполняется через header_map (nmID)
    # и не зависит от article_search_range. Параметр article_search_range влияет
    # только на интерпретацию start_row пользователем.

    # ========== ПОСТРОЕНИЕ КАРТЫ АРТИКУЛОВ ==========
    # Строим карту: артикул -> номер строки в таблице
    article_row_map = _build_article_row_map(
        service=service,
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name,
        header_map=header_map,
        start_row=start_row,
    )
    
    # Подготавливаем данные для записи
    value_ranges = []
    processed_rows = 0
    not_found_articles = 0
    
    for item in processed_data:
        nm_id = str(item.get('nmID', ''))
        if not nm_id or nm_id not in article_row_map:
            not_found_articles += 1
            logger.warning(f"Артикул {nm_id} не найден в таблице")
            continue
        
        row_num = article_row_map[nm_id]
        processed_rows += 1
        
        # Записываем значения по сегментам, чтобы соответствовать реальному расположению колонок
        for segment in segments:
            segment_keys = [key for key, _ in segment]
            segment_values = [_get_value_for_key(item, key) for key in segment_keys]

            if processed_rows <= 3:
                logger.debug(
                    "Записываем артикул %s в строку %s (колонки %s): %s",
                    nm_id,
                    row_num,
                    [info.letter for _, info in segment],
                    segment_values,
                )

            if segment_values:
                range_name = header_map.build_row_range(segment_keys, row_num)
                value_ranges.append({"range": range_name, "values": [segment_values]})
    
    # Выполняем запись с разбивкой на батчи (Google Sheets API ограничение)
    if value_ranges:
        batch_size = 100  # API ограничивает количество диапазонов, но логируем только ячейки
        total_written_cells = 0

        total_cells = sum(len(entry.get("values", [[]])[0]) for entry in value_ranges)
        print(f"📝 Записываем {total_cells} ячеек батчами...")
        
        for i in range(0, len(value_ranges), batch_size):
            batch = value_ranges[i:i + batch_size]
            
            try:
                body = {"valueInputOption": "RAW", "data": batch}
                service.spreadsheets().values().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
                batch_cells = sum(len(entry.get("values", [[]])[0]) for entry in batch)
                total_written_cells += batch_cells
                print(
                    f"   • Записано батч {i//batch_size + 1}: {batch_cells} ячеек (всего: {total_written_cells})"
                )

                # Небольшая задержка между батчами
                if i + batch_size < len(value_ranges):
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Ошибка записи батча {i//batch_size + 1}: {e}")
                continue
        
        print(f"✅ Запись завершена! Всего записано ячеек: {total_written_cells}")
    else:
        print("ℹ️ Нет данных для записи")
    
    # Логирование статистики
    print(f"📊 Статистика записи:")
    print(f"   • Обработано артикулов: {processed_rows}")
    print(f"   • Артикулов не найдено: {not_found_articles}")
    print(f"   • Всего артикулов в данных: {len(processed_data)}")
    
    # Автоформатирование процентных колонок, если они присутствуют
    try:
        percent_keys = [k for k in ("discount", "discountOnSite") if any(k == ck for ck, _ in column_infos)]
        if percent_keys:
            sheet_id = _get_sheet_id_by_title(service, spreadsheet_id, sheet_name)
            if sheet_id is not None:
                requests = []
                for key in percent_keys:
                    info = next((info for k, info in column_infos if k == key), None)
                    if info is None:
                        continue
                    # Форматируем со start_row до конца листа
                    requests.append({
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": start_row - 1,
                                "startColumnIndex": info.index,
                                "endColumnIndex": info.index + 1
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "numberFormat": {"type": "PERCENT", "pattern": "0.00%"}
                                }
                            },
                            "fields": "userEnteredFormat.numberFormat"
                        }
                    })
                if requests:
                    service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body={"requests": requests}
                    ).execute()
    except Exception as e:
        logger.warning(f"Не удалось применить формат процентов: {e}")

    return {
        "processed_rows": processed_rows,
        "not_found_articles": not_found_articles
    }


def get_sheet_info(spreadsheet_id: str = GOOGLE_SHEET_ID_UNIT_ECONOMICS) -> List[Dict[str, str]]:
    """
    Получает информацию о листах в таблице.
    
    Returns:
        List[Dict]: Список листов с их ID и названиями
    """
    service = _get_service(credentials_info)
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get('sheets', [])
    
    result = []
    for sheet in sheets:
        properties = sheet.get('properties', {})
        result.append({
            'id': properties.get('sheetId'),
            'title': properties.get('title')
        })
    
    return result
