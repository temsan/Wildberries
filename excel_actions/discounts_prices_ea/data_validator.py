"""
Data validator for discounts_prices data.

Функция для проверки целостности данных между API и Google таблицей.
Сравнивает данные из API с данными, записанными в Google таблицу.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple
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
GOOGLE_SHEET_NAME_DISCOUNTS_PRICES = getattr(api_keys_module, "GOOGLE_SHEET_NAME_DISCOUNTS_PRICES", "юнитка")

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


def _col_index_to_label(index_1based: int) -> str:
    """Конвертирует индекс столбца (1-based) в буквенное обозначение (A, B, C, ...)."""
    label = ""
    n = index_1based
    while n > 0:
        n, rem = divmod(n - 1, 26)
        label = chr(65 + rem) + label
    return label


def _col_letters_to_index(col_letters: str) -> int:
    """Конвертирует буквенное обозначение столбца (A, B, C, ...) в индекс (1-based)."""
    idx = 0
    for ch in col_letters:
        idx = idx * 26 + (ord(ch.upper()) - 64)
    return idx


def _batch_read_sheet_data(
    service,
    spreadsheet_id: str,
    sheet_name: str,
    header_map,
    start_row: int,
    column_keys: Iterable[str],
) -> Tuple[Dict[str, int], Dict[str, Dict[str, Any]]]:
    """
    Читает все данные из Google Sheets за один batch-запрос.
    
    Args:
        service: Google Sheets API service
        spreadsheet_id: ID таблицы
        sheet_name: Название листа
        article_col: Столбец с артикулами
        start_row: Начальная строка данных
        columns_order: Порядок столбцов для чтения
        
    Returns:
        Tuple[Dict[str, int], Dict[str, Dict[str, Any]]]: 
        (article_row_map, sheet_data)
    """
    
    # Сначала читаем все артикулы
    nm_header = header_map.get("nmID")
    print(f"📋 Читаем артикулы из столбца {nm_header.letter}...")
    article_range = header_map.build_column_range("nmID", start_row)
    article_res = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, 
        range=article_range
    ).execute()
    article_values = article_res.get('values', [])
    
    # Строим карту артикулов
    article_row_map = {}
    for offset, row_vals in enumerate(article_values, start=0):
        cell = row_vals[0].strip() if row_vals else ""
        if not cell:
            continue
        row_num = start_row + offset
        article = str(cell)
        
        # Пропускаем заголовки (не числовые значения)
        if not article.isdigit():
            print(f"⚠️ Пропускаем заголовок в строке {row_num}: '{article}'")
            continue
            
        if article not in article_row_map:
            article_row_map[article] = row_num
    
    print(f"📊 Найдено {len(article_row_map)} артикулов в таблице")
    
    if not article_row_map:
        return article_row_map, {}
    
    # Читаем данные по каждому ключу отдельно (устойчиво к пропускам и разрывам колонок)
    # Формируем список диапазонов для batchGet
    ranges = [header_map.build_column_range(key, start_row) for key in column_keys]
    if ranges:
        print(f"📋 Читаем данные по {len(ranges)} колонкам...")
        batch_res = service.spreadsheets().values().batchGet(
            spreadsheetId=spreadsheet_id,
            ranges=ranges,
            valueRenderOption='UNFORMATTED_VALUE',
            dateTimeRenderOption='SERIAL_NUMBER',
        ).execute()
        value_ranges = batch_res.get('valueRanges', [])
    else:
        value_ranges = []

    # Инициализируем контейнер
    sheet_data: Dict[str, Dict[str, Any]] = {}

    # Вспомогательные функции приведения типов
    def _parse_numeric(value: Any) -> float:
        try:
            if isinstance(value, str) and ',' in value:
                value = value.replace(',', '.')
            return float(value) if value not in (None, "") else 0.0
        except (ValueError, TypeError):
            return 0.0

    def _parse_bool(value: Any) -> bool:
        return str(value).lower() in ['true', '1', 'да', 'yes']

    # Разбираем ответы по порядку ключей
    for key_idx, col_name in enumerate(column_keys):
        if key_idx >= len(value_ranges):
            continue
        vr = value_ranges[key_idx]
        col_values = vr.get('values', [])

        for offset, row_vals in enumerate(col_values, start=0):
            row_num = start_row + offset
            # Находим артикул для этой строки
            # Быстрее держать обратную карту: row -> article
            # Построим на лету один раз
            # (переносим из article_row_map)
            # Инициализируем sheet_row
            # Пропускаем пустые
            article = None
            for art, art_row in article_row_map.items():
                if art_row == row_num:
                    article = art
                    break
            if not article:
                continue

            row_value = row_vals[0] if row_vals else ""
            if article not in sheet_data:
                sheet_data[article] = {}

            if col_name in ["prices", "discount", "discountedPrices", "discountOnSite", "priceafterSPP", "competitivePrice"]:
                sheet_data[article][col_name] = _parse_numeric(row_value)
            elif col_name in ["isCompetitivePrice", "hasPromotions"]:
                sheet_data[article][col_name] = _parse_bool(row_value)
            else:
                sheet_data[article][col_name] = row_value

    print(f"📊 Прочитано данных для {len(sheet_data)} артикулов")
    return article_row_map, sheet_data


def _legacy_read_sheet_data(
    service,
    spreadsheet_id: str,
    sheet_name: str,
    article_col: str,
    start_row: int,
    column_keys: List[str]
) -> Tuple[Dict[str, int], Dict[str, Dict[str, Any]]]:
    """
    Старый способ чтения данных (построчно с rate limiting).
    Используется для отладки или когда batch-чтение недоступно.
    """
    
    # Строим карту артикулов из таблицы
    article_row_map = {}
    try:
        rng = f"{sheet_name}!{article_col}{start_row}:{article_col}"
        res = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=rng).execute()
        values = res.get('values', [])
        
        for offset, row_vals in enumerate(values, start=0):
            cell = row_vals[0].strip() if row_vals else ""
            if not cell:
                continue
            row_num = start_row + offset
            article = str(cell)
            if article not in article_row_map:
                article_row_map[article] = row_num
    except Exception as e:
        logger.error(f"Ошибка чтения артикулов из таблицы: {e}")
        return {}, {}
    
    # Читаем данные из таблицы для найденных артикулов с rate limiting
    sheet_data = {}
    total_articles = len(article_row_map)
    processed_count = 0
    
    print(f"📊 Читаем данные для {total_articles} артикулов с rate limiting...")
    print(f"   • Задержка между запросами: 1.2 сек")
    print(f"   • Ожидаемое время: ~{total_articles * 1.2 / 60:.1f} мин")
    
    # Определяем начальный столбец для чтения данных
    article_col_index = _col_letters_to_index(article_col)
    start_col_index = article_col_index + 1
    start_col_letter = _col_index_to_label(start_col_index)
    
    for article, row_num in article_row_map.items():
        try:
            # Rate limiting: задержка между запросами
            if processed_count > 0:
                time.sleep(1.2)
            
            # Читаем строку с данными
            end_col_index = start_col_index + len(column_keys) - 1
            end_col_letter = _col_index_to_label(end_col_index)
            data_range = f"{sheet_name}!{start_col_letter}{row_num}:{end_col_letter}{row_num}"
            
            res = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=data_range).execute()
            values = res.get('values', [])
            
            if values and values[0]:
                row_data = values[0]
                # Создаем словарь с данными из таблицы
                sheet_row = {}
                for i, col_name in enumerate(column_keys):
                    if i < len(row_data):
                        value = row_data[i]
                        # Преобразуем значения к нужным типам
                        if col_name in ["prices", "discount", "discountedPrices", "discountOnSite", "priceafterSPP", "competitivePrice"]:
                            try:
                                sheet_row[col_name] = float(value) if value else 0.0
                            except (ValueError, TypeError):
                                sheet_row[col_name] = 0.0
                        elif col_name in ["isCompetitivePrice", "hasPromotions"]:
                            sheet_row[col_name] = str(value).lower() in ['true', '1', 'да', 'yes']
                        else:
                            sheet_row[col_name] = value
                    else:
                        # Если данных нет, используем значения по умолчанию
                        if col_name in ["prices", "discount", "discountedPrices", "discountOnSite", "priceafterSPP", "competitivePrice"]:
                            sheet_row[col_name] = 0.0
                        elif col_name in ["isCompetitivePrice", "hasPromotions"]:
                            sheet_row[col_name] = False
                        else:
                            sheet_row[col_name] = ""
                
                sheet_data[article] = sheet_row
            
            processed_count += 1
            if processed_count % 10 == 0:  # Прогресс каждые 10 артикулов
                print(f"   • Обработано: {processed_count}/{total_articles} ({processed_count/total_articles*100:.1f}%)")
                
        except Exception as e:
            logger.warning(f"Ошибка чтения данных для артикула {article}: {e}")
            processed_count += 1
            continue
    
    return article_row_map, sheet_data


def check_data_completeness(
    sheet_data: Dict[str, Dict[str, Any]], 
    column_keys: List[str]
) -> Dict[str, Any]:
    """
    Проверяет полноту данных в Google Sheets.
    
    Args:
        sheet_data: Данные из таблицы
        columns_order: Порядок столбцов для проверки
        
    Returns:
        Dict с результатами проверки полноты
    """
    
    print(f"🔍 Проверяем полноту данных в {len(sheet_data)} артикулах...")
    
    total_articles = len(sheet_data)
    empty_articles = 0
    incomplete_articles = 0
    complete_articles = 0
    
    empty_fields = {col: 0 for col in column_keys}
    incomplete_details = []
    
    for article, row_data in sheet_data.items():
        has_empty_fields = False
        article_empty_fields = []
        
        for col_name in column_keys:
            value = row_data.get(col_name, 0)
            
            # Проверяем, является ли значение "пустым"
            is_empty = False
            if col_name in ["prices", "discount", "discountedPrices", "discountOnSite", "priceafterSPP", "competitivePrice"]:
                is_empty = value == 0.0 or value is None
            elif col_name in ["isCompetitivePrice", "hasPromotions"]:
                is_empty = value is False  # False считается пустым для булевых полей
            else:
                is_empty = not value or str(value).strip() == ""
            
            if is_empty:
                empty_fields[col_name] += 1
                article_empty_fields.append(col_name)
                has_empty_fields = True
        
        if not article_empty_fields:
            complete_articles += 1
        elif len(article_empty_fields) == len(column_keys):
            empty_articles += 1
        else:
            incomplete_articles += 1
            incomplete_details.append({
                "article": article,
                "empty_fields": article_empty_fields
            })
    
    # Статистика по полям
    field_stats = {
        col_name: {
            "empty_count": empty_fields[col_name],
            "empty_percentage": (empty_fields[col_name] / total_articles * 100) if total_articles > 0 else 0,
        }
        for col_name in column_keys
    }
    
    result = {
        "total_articles": total_articles,
        "complete_articles": complete_articles,
        "incomplete_articles": incomplete_articles,
        "empty_articles": empty_articles,
        "field_stats": field_stats,
        "incomplete_details": incomplete_details[:10],  # Первые 10 для примера
        "completeness_percentage": (complete_articles / total_articles * 100) if total_articles > 0 else 0
    }
    
    # Выводим результаты
    print(f"📊 Результаты проверки полноты:")
    print(f"   • Всего артикулов: {total_articles}")
    print(f"   • Полностью заполненных: {complete_articles} ({result['completeness_percentage']:.1f}%)")
    print(f"   • Частично заполненных: {incomplete_articles}")
    print(f"   • Пустых: {empty_articles}")
    
    print(f"\n📋 Статистика по полям:")
    for col_name, stats in field_stats.items():
        print(f"   • {col_name}: {stats['empty_count']} пустых ({stats['empty_percentage']:.1f}%)")
    
    
    return result


def validate_data_integrity(
    processed_data: List[Dict[str, Any]],
    # ========== НАСТРОЙКИ - ИЗМЕНИТЕ ПРИ НЕОБХОДИМОСТИ ==========
    sheet_name: str = GOOGLE_SHEET_NAME_DISCOUNTS_PRICES,  # Название листа для проверки
    article_search_range: str = "A:A",  # Диапазон поиска артикулов
    start_row: int = 1,  # Начальная строка данных
    use_batch_reading: bool = True,  # Использовать batch-чтение (рекомендуется)
    # ============================================
    spreadsheet_id: str = GOOGLE_SHEET_ID_UNIT_ECONOMICS,
    credentials_info: Dict[str, Any] = None,  # Google credentials (из api_keys.py)
) -> Dict[str, Any]:
    """
    Проверяет целостность данных между API и Google таблицей.
    
    Сравнивает данные из API с данными, записанными в Google таблицу.
    Проверяет соответствие всех полей: prices, discount, discountedPrices, etc.
    
    Args:
        processed_data: Обработанные данные из data_processor
        sheet_name: Название листа для проверки
        article_search_range: Диапазон поиска артикулов
        start_row: Начальная строка данных
        use_batch_reading: Использовать batch-чтение (рекомендуется)
        spreadsheet_id: ID Google таблицы
        
    Returns:
        Dict с результатами проверки:
        {
            "total_checked": int,           # Всего проверено артикулов
            "perfect_matches": int,         # Полностью совпадающих
            "mismatches": int,              # Несовпадений
            "not_found_in_sheet": int,      # Не найдено в таблице
            "mismatch_details": List[Dict], # Детали несовпадений
            "validation_passed": bool       # Прошла ли валидация
        }
    """
    
    print(f"🔍 Начинаем проверку целостности данных в листе '{sheet_name}'...")
    print(f"🔧 Режим: {'Batch-чтение' if use_batch_reading else 'Построчное чтение'}")
    
    service = _get_service(credentials_info)
    
    # Подготавливаем карту заголовков
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

    nm_header = header_map.get("nmID")
    print(f"📋 Столбец с артикулами: {nm_header.letter}")

    # Используем только доступные ключи колонок и логируем найденные/пропущенные
    resolved_pairs = [(k, header_map.get_optional(k)) for k in DATA_COLUMN_KEYS]
    column_keys = [k for k, info in resolved_pairs if info is not None]
    skipped_keys = [k for k, info in resolved_pairs if info is None]
    if skipped_keys:
        logger.info("Пропущены отсутствующие колонки: %s", ", ".join(skipped_keys))
    if column_keys:
        logger.info("Найдены колонки для проверки: %s", ", ".join(column_keys))
    
    # Читаем данные из таблицы
    try:
        if use_batch_reading:
            # Используем batch-чтение (быстро и надежно)
            article_row_map, sheet_data = _batch_read_sheet_data(
                service=service,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                header_map=header_map,
                start_row=start_row,
        column_keys=column_keys,
            )
        else:
            # Старый способ (медленный, но может быть полезен для отладки)
            article_row_map, sheet_data = _legacy_read_sheet_data(
                service,
                spreadsheet_id,
                sheet_name,
                header_map.get("nmID").letter,
                start_row,
                column_keys,
            )
    except Exception as e:
        logger.error(f"Ошибка чтения данных из таблицы: {e}")
        return {"error": str(e)}
    
    # Проверяем полноту данных в таблице
    print(f"\n🔍 Проверяем полноту данных в Google Sheets...")
    completeness_result = check_data_completeness(sheet_data, column_keys)
    
    # Сравниваем данные
    total_checked = 0
    perfect_matches = 0
    mismatches = 0
    not_found_in_sheet = 0
    mismatch_details = []
    
    for item in processed_data:
        nm_id = str(item.get('nmID', ''))
        if not nm_id:
            continue
            
        total_checked += 1
        
        if nm_id not in sheet_data:
            not_found_in_sheet += 1
            continue
        
        # Сравниваем каждое поле
        sheet_row = sheet_data[nm_id]
        item_mismatches = []
        
        for col_name in column_keys:
            api_value = item.get(col_name, 0)
            sheet_value = sheet_row.get(col_name, 0)

            # Сравниваем значения с учетом типов и форматов (проценты в листе как доля)
            if col_name in ["prices", "discount", "discountedPrices", "discountOnSite", "priceafterSPP", "competitivePrice"]:
                api_num = float(api_value)
                sheet_num = float(sheet_value)
                # Нормализация для процентных полей: в листе хранится доля (0.3), в API — проценты (30)
                if col_name in ["discount", "discountOnSite"]:
                    sheet_num = sheet_num * 100
                if abs(api_num - sheet_num) > 0.01:
                    item_mismatches.append({
                        "field": col_name,
                        "api_value": api_value,
                        "sheet_value": sheet_value
                    })
            else:
                # Для булевых значений
                if bool(api_value) != bool(sheet_value):
                    item_mismatches.append({
                        "field": col_name,
                        "api_value": api_value,
                        "sheet_value": sheet_value
                    })
        
        if item_mismatches:
            mismatches += 1
            mismatch_details.append({
                "nm_id": nm_id,
                "mismatches": item_mismatches
            })
        else:
            perfect_matches += 1
    
    # Определяем, прошла ли валидация
    # Валидация проходит, если нет несовпадений (не найдено в таблице - это нормально)
    validation_passed = mismatches == 0
    
    result = {
        "total_checked": total_checked,
        "perfect_matches": perfect_matches,
        "mismatches": mismatches,
        "not_found_in_sheet": not_found_in_sheet,
        "mismatch_details": mismatch_details,
        "validation_passed": validation_passed,
        "completeness_result": completeness_result
    }
    
    # Выводим результаты
    print(f"📊 Результаты проверки целостности:")
    print(f"   • Всего проверено: {total_checked}")
    print(f"   • Полностью совпадающих: {perfect_matches}")
    print(f"   • Несовпадений: {mismatches}")
    print(f"   • Не найдено в таблице: {not_found_in_sheet}")
    print(f"   • Валидация {'✅ ПРОШЛА' if validation_passed else '❌ НЕ ПРОШЛА'}")
    
    if mismatch_details:
        print(f"\n🔍 Детали несовпадений (первые 5):")
        for i, detail in enumerate(mismatch_details[:5]):
            print(f"   • Артикул {detail['nm_id']}:")
            for mismatch in detail['mismatches']:
                print(f"     - {mismatch['field']}: API={mismatch['api_value']}, Sheet={mismatch['sheet_value']}")
    
    return result


def print_validation_report(result: Dict[str, Any]) -> None:
    """
    Выводит подробный отчет о валидации данных.
    
    Args:
        result: Результат валидации из validate_data_integrity
    """
    print("\n" + "="*80)
    print("📊 ОТЧЕТ О ВАЛИДАЦИИ ДАННЫХ")
    print("="*80)
    
    print(f"📦 Всего артикулов проверено: {result['total_checked']}")
    print(f"✅ Полностью совпадающих: {result['perfect_matches']}")
    print(f"❌ Несовпадений: {result['mismatches']}")
    print(f"🔍 Не найдено в таблице: {result['not_found_in_sheet']}")
    
    
    if result['mismatches'] > 0:
        print(f"\n🔍 ДЕТАЛИ НЕСОВПАДЕНИЙ:")
        for detail in result['mismatch_details']:
            print(f"\n   Артикул {detail['nm_id']}:")
            for mismatch in detail['mismatches']:
                print(f"     • {mismatch['field']}: API={mismatch['api_value']}, Sheet={mismatch['sheet_value']}")
    
    print(f"\n🎯 ИТОГ: {'✅ ВАЛИДАЦИЯ ПРОШЛА' if result['validation_passed'] else '❌ ВАЛИДАЦИЯ НЕ ПРОШЛА'}")
    print("="*80)
