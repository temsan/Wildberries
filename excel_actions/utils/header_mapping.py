"""Утилиты для динамического сопоставления заголовков Google Sheets.

Базовый каркас: чтение строки заголовков, нормализация названий
и построение карты «логический ключ → информация о колонке».

TODO (дальнейшие шаги):
- Добавить поддержку алиасов/регулярных шаблонов;
- Расширить обработку ошибок и отчётность;
- Интегрировать с конкретными пайплайнами excel_actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class HeaderInfo:
    """Информация об одном заголовке таблицы."""

    title: str
    index: int  # zero-based
    letter: str


class HeaderMappingError(Exception):
    """Ошибка построения карты заголовков."""


def _column_index_to_letter(index_zero_based: int) -> str:
    """Преобразует индекс колонки (0-based) в обозначение Google Sheets (A, B, ...)."""

    if index_zero_based < 0:
        raise ValueError("column index must be non-negative")

    result = ""
    index = index_zero_based
    while True:
        index, remainder = divmod(index, 26)
        result = chr(65 + remainder) + result
        if index == 0:
            break
        index -= 1
    return result


def _normalize_header(title: str) -> str:
    """Нормализует имя заголовка (trim + нижний регистр + схлопывание пробелов)."""

    stripped = title.strip()
    if not stripped:
        return ""
    return " ".join(stripped.lower().split())


def quote_sheet_name(sheet_name: str) -> str:
    """Возвращает корректное имя листа для диапазонов (с кавычками при необходимости)."""

    return f"'{sheet_name}'" if " " in sheet_name or sheet_name.startswith("'") else sheet_name


def fetch_headers(
    service,
    spreadsheet_id: str,
    sheet_name: str,
    header_row: int = 1,
) -> List[str]:
    """Считывает строку заголовков из Google Sheets и возвращает список ячеек."""

    if header_row < 1:
        raise ValueError("header_row must be >= 1")

    # Пробуем получить Sheet ID по названию листа
    try:
        # Получаем метаданные таблицы
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = spreadsheet.get('sheets', [])

        # Ищем лист по названию
        sheet_id = None
        for sheet in sheets:
            if sheet['properties']['title'] == sheet_name:
                sheet_id = sheet['properties']['sheetId']
                break

        if sheet_id is None:
            print(f"Лист '{sheet_name}' не найден в таблице")
            return []

        # Используем Sheet ID вместо названия
        range_template = f"{header_row}:{header_row}"
        response = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_template)
            .execute()
        )

    except Exception as e:
        print(f"Ошибка при получении Sheet ID: {e}")
        # Fallback к старому методу
        sheet_ref = sheet_name
        range_template = f"{sheet_ref}!{header_row}:{header_row}"
        response = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_template)
            .execute()
        )
    values = response.get("values", [])
    if not values:
        return []
    # API возвращает список списков; берём первую (единственную) строку.
    return values[0]


class HeaderMap:
    """Карта соответствия заголовков настройкам."""

    def __init__(
        self,
        sheet_name: str,
        header_row: int,
        headers: Sequence[str],
        expected: Mapping[str, Iterable[str]],
    ) -> None:
        self.sheet_name = sheet_name
        self.header_row = header_row
        self._headers = list(headers)
        self._expected = expected

        self._normalized: Dict[str, HeaderInfo] = {}
        self.missing: List[str] = []
        self._build()

    # region public API -------------------------------------------------
    def get(self, key: str) -> HeaderInfo:
        try:
            return self._normalized[key]
        except KeyError as exc:
            raise HeaderMappingError(f"Header '{key}' is not mapped") from exc

    def get_optional(self, key: str) -> Optional[HeaderInfo]:
        return self._normalized.get(key)

    def iter_infos(self, keys: Sequence[str]) -> Iterable[HeaderInfo]:
        for key in keys:
            info = self.get_optional(key)
            if info is not None:
                yield info

    def require_all(self) -> None:
        if self.missing:
            raise HeaderMappingError(
                "Missing required headers: " + ", ".join(sorted(self.missing))
            )

    def build_column_range(
        self,
        key: str,
        start_row: int,
        end_row: Optional[int] = None,
    ) -> str:
        info = self.get(key)
        sheet_ref = quote_sheet_name(self.sheet_name)
        if end_row is None:
            return f"{sheet_ref}!{info.letter}{start_row}:{info.letter}"
        return f"{sheet_ref}!{info.letter}{start_row}:{info.letter}{end_row}"

    def build_cell_ref(self, key: str, row: int) -> str:
        info = self.get(key)
        sheet_ref = quote_sheet_name(self.sheet_name)
        return f"{sheet_ref}!{info.letter}{row}"

    def build_row_range(self, keys: Sequence[str], row: int) -> str:
        if not keys:
            raise ValueError("keys must not be empty")
        infos = [self.get(k) for k in keys]
        infos.sort(key=lambda info: info.index)
        sheet_ref = quote_sheet_name(self.sheet_name)
        start = f"{infos[0].letter}{row}"
        end = f"{infos[-1].letter}{row}"
        return f"{sheet_ref}!{start}:{end}"

    def build_columns_span(self, keys: Sequence[str], start_row: int) -> str:
        if not keys:
            raise ValueError("keys must not be empty")
        infos = [self.get(k) for k in keys]
        infos.sort(key=lambda info: info.index)
        sheet_ref = quote_sheet_name(self.sheet_name)
        start = infos[0].letter
        end = infos[-1].letter
        # Возвращаем диапазон от start_row до конца листа между start и end столбцами
        # Например: 'Лист1'!C2:J — прочитать все строки с 2-й до конца между колонками C и J
        return f"{sheet_ref}!{start}{start_row}:{end}"

    # endregion ---------------------------------------------------------

    def _build(self) -> None:
        normalized_headers: Dict[str, List[Tuple[int, str]]] = {}
        for idx, raw_title in enumerate(self._headers):
            normalized = _normalize_header(raw_title)
            if not normalized:
                continue
            normalized_headers.setdefault(normalized, []).append((idx, raw_title))

        for key, aliases in self._expected.items():
            match_info = self._match_header(key, aliases, normalized_headers)
            if match_info is None:
                self.missing.append(key)
                continue
            index, title = match_info
            letter = _column_index_to_letter(index)
            self._normalized[key] = HeaderInfo(title=title, index=index, letter=letter)

    def _match_header(
        self,
        key: str,
        aliases: Iterable[str],
        normalized_headers: Dict[str, List[Tuple[int, str]]],
    ) -> Optional[Tuple[int, str]]:
        candidates = list(aliases) or [key]
        normalized_candidates = [_normalize_header(candidate) for candidate in candidates]

        for normalized in normalized_candidates:
            if normalized in normalized_headers:
                matches = normalized_headers[normalized]
                if len(matches) > 1:
                    titles = [title for _, title in matches]
                    raise HeaderMappingError(
                        f"Header '{normalized}' matched multiple columns: {titles}"
                    )
                return matches[0]
        return None


def build_header_map(
    headers: Sequence[str],
    sheet_name: str,
    header_row: int,
    expected_headers: Mapping[str, Iterable[str]],
) -> HeaderMap:
    """Создаёт HeaderMap без обращения к Google API."""

    return HeaderMap(
        sheet_name=sheet_name,
        header_row=header_row,
        headers=headers,
        expected=expected_headers,
    )


def load_header_map(
    service,
    spreadsheet_id: str,
    sheet_name: str,
    expected_headers: Mapping[str, Iterable[str]],
    header_row: int = 1,
) -> HeaderMap:
    """Читает заголовки из Google Sheets и создаёт HeaderMap."""

    headers = fetch_headers(service, spreadsheet_id, sheet_name, header_row=header_row)
    return build_header_map(headers, sheet_name, header_row, expected_headers)

