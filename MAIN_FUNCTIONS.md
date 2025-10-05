## MAIN FUNCTIONS

Краткое описание корневой логики и основных сценариев запуска.

### Слои архитектуры
- `wb_api/*` — HTTP‑клиенты WB API
- `excel_actions/*` — работа с Google Sheets (чтение/запись/валидация)
- `main_function/*` — сценарии верхнего уровня (оркестрация шагов)
- `api_keys.py` — единая конфигурация и профили (`ACTIVE_USER`)

Правила:
- Не хардкодить значения: использовать профили и динамические параметры
- Секреты храним вне git (inline в `api_keys.py` или локальный файл)

---

## supplier_stock — Остатки по складам (Statistics API) ⚠️ ОТКЛЮЧЕНО
Файл: `WB/main_function/supplier_stock_mf/supplier_stock.py`

**⚠️ ВНИМАНИЕ: Эта функция ОТКЛЮЧЕНА!**
Используйте `warehouse_remains` вместо `supplier_stock` для получения остатков по складам.

### Как активировать функцию при необходимости:
1. Откройте файл `WB/main_function/supplier_stock_mf/supplier_stock.py`
2. Найдите функцию `main()`
3. Закомментируйте блок предупреждения
4. Раскомментируйте оригинальную логику функции
5. Сохраните файл

### Что делает цепочка
1) Тянет данные с `https://statistics-api.wildberries.ru/api/v1/supplier/stocks`.
2) Валидирует структуру первой страницы ответа (поля/типы).
3) Пагинация: запрашивает последующие страницы, подставляя `dateFrom = lastChangeDate` из последней строки предыдущего ответа.
4) Агрегирует данные:
   - per‑warehouse: по `(nmId, warehouseName)` суммирует `quantity`, `inWayToClient`, `inWayFromClient`.
   - in‑way totals: по `nmId` суммирует только в пути (`inWayToClientTotal`, `inWayFromClientTotal`).
5) Читает из Google Sheets список артикулов (столбец D) и фильтрует данные по ним.
6) Очищает целевые ячейки на листе (только для строк артикулов, которые пришли в ответе API) и записывает:
   - per‑warehouse `quantity` по складам
   - тоталы в пути (`В пути к клиенту`, `В пути от клиента`)

### Параметры запуска
```bash
# Базовый запуск (полная цепочка)
python3 "WB/main_function/supplier_stock_mf/supplier_stock.py"

# Быстрый тест: первая страница без ожидания (для проверки доступа/структуры)
python3 "WB/main_function/supplier_stock_mf/supplier_stock.py" --max-pages 1 --no-throttle

# Указать стартовую дату (RFC3339, МСК)
python3 "WB/main_function/supplier_stock_mf/supplier_stock.py" --date-from 2024-01-01
```

### Выбор даты (dateFrom)
Приоритеты:
1) `MANUAL_DATE_FROM` — если непустая строка
2) `--date-from` — если указан флаг
3) По умолчанию: сегодня (МСК) минус 3 месяца

Рекомендация WB для полной выгрузки: максимально ранняя дата (в коде — `2019-06-20`).

### Ограничения и ожидание
- Лимит Statistics API: 1 запрос/мин.
- Пагинация требует последовательных запросов — код ждёт 61 секунду между страницами (есть явное сообщение в логах перед паузой).
- Для быстрых проверок используйте `--max-pages 1 --no-throttle`.

### Валидатор структуры
Файл: `WB/excel_actions/supplier_stock_ea/structure_validator.py`
- Проверяет обязательные поля и типы первой страницы.
- При несовпадении структуры задаёт интерактивный вопрос: продолжать или остановиться.

### Агрегации
Файл: `WB/excel_actions/supplier_stock_ea/transform.py`
- `aggregate_per_warehouse(rows)` → список по `(nmId, warehouseName)` с суммами `quantity`, `inWayToClient`, `inWayFromClient`.
- `aggregate_inway_totals(rows)` → по `nmId` суммарные `inWayToClientTotal`, `inWayFromClientTotal`.

### Чтение списка артикулов и фильтрация
Файлы:
- `WB/excel_actions/supplier_stock_ea/article_list_reader.py` — читает `D3:D1000` листа `Остатки по складам` из таблицы `GOOGLE_SHEET_ID`.
- `WB/excel_actions/supplier_stock_ea/article_filter.py` — фильтрует данные по списку `nmId`.

### Запись в Google Sheets (райтер)
Файл: `WB/excel_actions/supplier_stock_ea/google_writer.py`
- Диапазон заголовка: `A1:CA1` (из первой строки читаются названия колонок/складов).
- Столбец артикулов: `D`, строки `3..1000`.
- Текст заголовков тоталов (точное совпадение):
  - `В пути к клиенту`
  - `В пути от клиента`
- Функции:
  - `clear_target_cells(spreadsheet_id, sheet_name, header_range, article_col, start_row, warehouses_expected, total_to_client_header, total_from_client_header, allowed_nm_ids=None)`
    - Если `allowed_nm_ids` не передан — очищает под всеми указанными колонками для всех строк, где в D есть значение.
    - Если `allowed_nm_ids` передан — очищает только **те** строки, чей `nmId` присутствует и в листе (D) и в `allowed_nm_ids` (из API).
  - `write_per_warehouse_and_totals(...)`
    - Пишет per‑warehouse `quantity` и тоталы в пути.
    - Отчитывается, какие склады обнаружены в API, но отсутствуют в шапке листа.

### Поведение с дубликатами в колонке D
- Если в D встречаются дубли `nmId`, используется **первая** встреченная строка (strategy “first wins”).

### Точки контроля/диагностика
- Маска API‑ключа печатается при старте.
- Перед паузой выводится сообщение на 61 сек.
- Валидатор даёт интерактивный выбор при изменениях схемы.
- При записи в таблицу выводится число очищенных/записанных ячеек и список отсутствующих колонок для складов.

### Типичные ошибки и их причины
- `401 Unauthorized` — неверный/просроченный токен или токен не от Statistics API нужного кабинета.
- Пустой ответ — слишком поздний `dateFrom` или нет данных по заданному интервалу.
- Нет изменения в таблице — в шапке нет колонок для соответствующих складов, либо артикулы из API отсутствуют в D‑колонке листа.

---

## warehouse_remains — Полная цепочка обработки остатков товаров 🏬
Файл: `WB/main_function/warehouse_remains_mf/warehouse_remains.py`

### Что делает main функция
Полная интегрированная цепочка получения, валидации, агрегации и записи данных об остатках товаров через Wildberries API с последующей валидацией записанных данных.

### Основные этапы работы
1) **Получение данных** — загружает данные через API или тестовые данные
2) **Валидация структуры** — проверяет корректность структуры полученных данных
3) **Агрегация данных** — группирует данные по barcode с суммированием по складам
4) **Статистика и примеры** — выводит аналитику и примеры агрегированных данных
5) **Запись в Google Sheets** — сохраняет данные в таблицу с очисткой старых данных
6) **Валидация записанных данных** — сравнивает записанные данные с исходными

### Структура main функции

#### Основная функция: `main()`
```python
def main():
    """Основная функция warehouse_remains с полной интеграцией."""
```

**Процесс выполнения:**
1. Получение данных из API (или загрузка тестовых)
2. Валидация структуры данных
3. Агрегация данных по barcode
4. Вывод статистики и примеров
5. Запись в Google Sheets
6. Валидация записанных данных

#### Вспомогательные функции

**1. `load_test_data()`** — Загрузка тестовых данных
- Загружает данные из `WB/wb_api/warehouse_remains_response.json`
- **ХАРДКОД:** Путь к файлу зафиксирован в коде
- Возвращает список данных или None при ошибке

**2. `test_validation_only()`** — Тест только валидации
- Тестирует валидацию структуры на тестовых данных
- **ХАРДКОД:** Использует только тестовые данные

**3. `test_aggregation_only()`** — Тест только агрегации
- Тестирует агрегацию данных на тестовых данных
- **ХАРДКОД:** Использует только тестовые данные

### Настройки (участки с хардкодом)

#### ⚠️ КРИТИЧЕСКИЕ ХАРДКОДЫ:
```python
# 1. Название листа Google Sheets
SHEET_NAME = "Остатки по складам"  # ⚠️ ПОДСТАВЬТЕ НАЗВАНИЕ ЛИСТА

# 2. Режим работы (тестовые данные vs реальный API)
USE_TEST_DATA = True  # ⚠️ True = тестовые данные, False = реальный API

# 3. Путь к тестовым данным
test_data_path = BASE_DIR / 'wb_api' / 'warehouse_remains_response.json'

# 4. URL Google таблицы
sheet_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/edit"
```

#### Динамические импорты (без хардкода):
```python
# API клиент
wb_api_path = BASE_DIR / 'wb_api' / 'warehouse_remains.py'

# Валидатор структуры
structure_validator_path = BASE_DIR / 'excel_actions' / 'warehouse_remains_ea' / 'structure_validator.py'

# Агрегатор данных
data_aggregator_path = BASE_DIR / 'excel_actions' / 'warehouse_remains_ea' / 'data_aggregator.py'

# Google Sheets writer
google_sheets_writer_path = BASE_DIR / 'excel_actions' / 'warehouse_remains_ea' / 'google_sheets_writer.py'

# Валидация данных
data_validator_path = BASE_DIR / 'excel_actions' / 'warehouse_remains_ea' / 'data_validator.py'

# API ключи
api_keys_path = BASE_DIR / 'api_keys.py'
```

### Алгоритм работы

#### Этап 1: Получение данных
```python
if USE_TEST_DATA:
    print("📊 Используем тестовые данные")
    report_data = load_test_data()
else:
    print("🌐 Используем реальный API")
    api = WildberriesWarehouseAPI(API_KEY)
    report_data = api.get_warehouse_remains()
```

#### Этап 2: Валидация структуры
```python
if not check_and_validate_structure(report_data):
    print("🛑 Выполнение остановлено из-за проблем со структурой данных")
    return
```

#### Этап 3: Агрегация данных
```python
aggregated_data = aggregate_warehouse_remains(report_data)
print(f"✅ Агрегировано {len(aggregated_data)} barcode")
```

#### Этап 4: Статистика и примеры
```python
print_aggregation_sample(aggregated_data, count=3)
print_warehouse_statistics(aggregated_data)
```

#### Этап 5: Запись в Google Sheets
```python
sheet_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/edit"
write_warehouse_remains_to_sheets(sheet_url, SHEET_NAME, aggregated_data)
```

#### Этап 6: Валидация записанных данных
```python
validation_passed = validate_warehouse_remains_data(sheet_url, SHEET_NAME, aggregated_data)
if validation_passed:
    print("✅ Валидация данных пройдена успешно")
else:
    print("⚠️ Валидация данных завершена с предупреждениями")
```

### Интеграция с модулями

#### 1. API клиент (`WB/wb_api/warehouse_remains.py`)
- **Функция:** `WildberriesWarehouseAPI.get_warehouse_remains()`
- **Назначение:** Получение данных об остатках через Seller Analytics API
- **ХАРДКОД:** API ключ берется из `api_keys.py`

#### 2. Валидатор структуры (`WB/excel_actions/warehouse_remains_ea/structure_validator.py`)
- **Функция:** `check_and_validate_structure()`
- **Назначение:** Проверка корректности структуры данных
- **ХАРДКОД:** Схема валидации зафиксирована в коде

#### 3. Агрегатор данных (`WB/excel_actions/warehouse_remains_ea/data_aggregator.py`)
- **Функции:** 
  - `aggregate_warehouse_remains()` — агрегация по barcode
  - `print_aggregation_sample()` — вывод примеров
  - `print_warehouse_statistics()` — статистика по складам
- **Назначение:** Группировка и анализ данных
- **ХАРДКОД:** Логика агрегации зафиксирована в коде

#### 4. Google Sheets Writer (`WB/excel_actions/warehouse_remains_ea/google_sheets_writer.py`)
- **Функция:** `write_warehouse_remains_to_sheets()`
- **Назначение:** Запись данных в Google Sheets
- **ХАРДКОД:** 
  - Название листа передается как параметр
  - Столбцы складов определяются динамически
  - Дополнительные столбцы: "В пути к клиенту", "В пути от клиента", "Объем упаковки"

#### 5. Валидация данных (`WB/excel_actions/warehouse_remains_ea/data_validator.py`)
- **Функция:** `validate_warehouse_remains_data()`
- **Назначение:** Сравнение записанных данных с исходными
- **ХАРДКОД:** 
  - Дополнительные поля для проверки: "В пути к клиенту", "В пути от клиента", "Объем упаковки"
  - Допуск для сравнения float: 0.01

### Запуск функции

#### Базовый запуск:
```bash
python3 WB/main_function/warehouse_remains_mf/warehouse_remains.py
```

#### Тестирование отдельных компонентов:
```bash
# Только валидация структуры
python3 WB/main_function/warehouse_remains_mf/warehouse_remains.py test-validation

# Только агрегация данных
python3 WB/main_function/warehouse_remains_mf/warehouse_remains.py test-aggregation
```

### Обрабатываемые поля
Функция обрабатывает следующие поля товаров:
1. `barcode` — штрихкод товара
2. `vendorCode` — код поставщика
3. `nmId` — артикул товара
4. `volume` — объем упаковки
5. `in_way_to_recipients` — в пути к получателям
6. `in_way_returns_to_warehouse` — в пути возвраты на склад
7. `warehouses` — остатки по складам (словарь {склад: количество})

### Статистика выполнения
Функция выводит подробную статистику:
- Общее количество товаров
- Количество агрегированных barcode
- Статистика по складам (топ-10 по количеству barcode и остатков)
- Аналитика по остаткам (общие суммы, в пути к/от клиента)
- Результаты валидации записанных данных

### Обработка ошибок
- **Ошибки загрузки данных** — остановка выполнения
- **Ошибки валидации структуры** — остановка выполнения
- **Ошибки агрегации** — остановка выполнения
- **Ошибки записи в Google Sheets** — остановка выполнения с рекомендациями
- **Ошибки валидации данных** — продолжение с предупреждениями

### Выходные данные
1. **Консольный вывод** — прогресс выполнения, статистика, результаты валидации
2. **Google Sheets** — обновленная таблица с данными об остатках
3. **Валидация** — детальный отчет о совпадении данных

### Критические точки для настройки
1. **`SHEET_NAME`** — название листа в Google Sheets
2. **`USE_TEST_DATA`** — переключение между тестовыми и реальными данными
3. **`GOOGLE_SHEET_ID`** — ID таблицы Google Sheets (в `api_keys.py`)
4. **`API_KEY`** — API ключ для Wildberries (в `api_keys.py`)
5. **Структура Google Sheets** — наличие нужных столбцов складов

### Важные моменты
- Используется `WB_API_TOKEN` для авторизации (Seller Analytics API)
- Структура данных отличается от `supplier_stock` (Statistics API)
- Валидация данных выполняется batch-запросами для оптимизации
- Очистка старых данных происходит только для найденных barcode

---

## Рекомендации по эксплуатации
- Для быстрых проверок используйте `--max-pages 1 --no-throttle`.
- Для полной выгрузки — без `--no-throttle`, с паузой 61 сек между страницами.
- Следите за заголовком первой строки листа: названия складов должны строго совпадать с `warehouseName` из API.
- При смене кабинета могут появляться новые склады — добавляйте их в шапку.
- При ошибках авторизации сверяйте маску ключа и источник (меняйте `IP_Nosov`).

### Важно: несколько баркодов для одного артикула (Content API)
- В Content API (`cards list`) у одной карточки `(nmID, vendorCode)` может быть несколько штрихкодов.
- Баркоды лежат в `sizes[].skus` и являются массивом строк.
- В базе артикулов мы создаём отдельную запись для каждой тройки `(nmID, barcode, vendorCode)`,
  чтобы корректно учитывать разные размеры/штрихкоды одного артикула.

---

## discounts_prices — Получение и обработка данных о скидках и ценах 💸 (опционально)
Файл: `WB/main_function/discounts_prices_mf/discounts_prices.py`

### Что делает main функция
Полная цепочка получения, обработки и валидации данных о товарах со скидками через Wildberries API. Функция обеспечивает полный цикл от получения данных до их записи в Google Sheets с проверкой целостности.

### Основные этапы работы
1) **Получение данных** — загружает ВСЕ товары через WBDiscountsPricesClient (все страницы)
2) **Валидация структуры** — проверяет корректность структуры полученных данных
3) **Обработка данных** — преобразует данные для отчета (цены, скидки, СПП)
4) **Анализ статистики** — анализирует пагинацию, категории и бренды
5) **Запись в Google Sheets** — сохраняет данные в таблицу
6) **Проверка целостности** — сравнивает данные API с записанными в таблице
7) **Логирование** — ведет подробный лог всего процесса

### Структура main функции

#### Основная функция: `main()`
```python
def main() -> int:
    """Основная функция обработки данных о скидках и ценах."""
```

**Параметры командной строки:**
- `--page-size` — размер страницы (по умолчанию 50)
- `--sleep-seconds` — задержка между запросами (по умолчанию 1.0)

**Возвращает:**
- `0` — успешное выполнение
- `1` — ошибка выполнения

#### Вспомогательные функции

**1. `import_discounts_client()`** — Импорт API клиента
- Динамически импортирует `WBDiscountsPricesClient`
- Путь: `WB/wb_api/discounts_prices/discounts_prices.py`

**2. `import_structure_validator()`** — Импорт валидатора структуры
- Импортирует функцию проверки структуры данных
- Путь: `WB/excel_actions/discounts_prices_ea/structure_validator.py`

**3. `import_data_processor()`** — Импорт обработчика данных
- Импортирует функции обработки и анализа данных
- Путь: `WB/excel_actions/discounts_prices_ea/data_processor.py`

**4. `analyze_goods_data()`** — Анализ данных товаров
- Анализирует классы товаров (subject) и бренды
- Подсчитывает статистику пагинации
- Возвращает структурированный анализ

**5. `print_analysis_report()`** — Вывод отчета анализа
- Форматированный вывод статистики по категориям и брендам
- Процентное распределение товаров

**6. `print_processed_data_report()`** — Вывод отчета по обработанным данным
- Детальная статистика по обработанным товарам
- Примеры первых 3 товаров с полными данными

**7. `save_json_response()`** — Сохранение JSON ответа
- Сохраняет полный ответ API в файл
- Включает метаданные и анализ данных

### Алгоритм работы

#### Этап 1: Получение данных
```python
# Создание клиента
client = WBDiscountsPricesClient()

# Получение всех товаров
all_goods = client.iterate_all_goods(
    page_size=args.page_size,
    sleep_seconds=args.sleep_seconds,
    max_pages=None  # Всегда обрабатываем все страницы
)
```

#### Этап 2: Валидация структуры
```python
# Формирование данных для валидации
response_data = {
    "data": {"listGoods": all_goods},
    "error": False,
    "errorText": "",
    "analysis": {},
    "metadata": {...}
}

# Запуск валидации
is_valid = validate_structure(response_data)
```

#### Этап 3: Обработка данных
```python
# Обработка данных для отчета
processed_data = process_data(all_goods)
summary = get_summary(processed_data)
```

#### Этап 4: Анализ и отчеты
```python
# Анализ данных
analysis = analyze_goods_data(all_goods)

# Вывод отчетов
print_analysis_report(analysis)
print_processed_data_report(processed_data, summary)
```

#### Этап 5: Запись в Google Sheets
```python
# Запись в таблицу
result = write_discounts_prices_to_sheet(processed_data)
```

#### Этап 6: Валидация целостности
```python
# Проверка целостности данных
validation_result = validate_data_integrity(processed_data)
print_validation_report(validation_result)
```

### Обрабатываемые поля
Функция обрабатывает следующие поля товаров:
1. `nmID` — артикул товара
2. `vendorCode` — код поставщика
3. `brand` — бренд
4. `subject` — класс товара
5. `prices` — цены товаров
6. `discount` — размер скидки (%)
7. `discountedPrices` — цены со скидкой
8. `discountOnSite` — скидка на сайте (%)
9. `priceafterSPP` — цена после СПП
10. `competitivePrice` — конкурентная цена
11. `isCompetitivePrice` — флаг конкурентной цены
12. `hasPromotions` — флаг наличия промоакций

### Логирование
Функция ведет подробное логирование:
- **Консольный вывод** — прогресс выполнения, статистика, отчеты
- **Файловое логирование** — `discounts_prices.log` в папке выполнения
- **Уровни логирования** — INFO, WARNING, ERROR

### Настройки Google Sheets
Настройки записи находятся в `WB/excel_actions/discounts_prices_ea/google_writer.py`:
- `sheet_name` — название листа
- `article_search_range` — диапазон поиска артикулов
- `start_row` — начальная строка данных

### Запуск функции
```bash
# Базовый запуск
python3 WB/main_function/discounts_prices_mf/discounts_prices.py

# С параметрами
python3 WB/main_function/discounts_prices_mf/discounts_prices.py --page-size 100 --sleep-seconds 0.5
```

### Выходные файлы
1. **`discounts_prices.log`** — лог выполнения
2. **`discounts_prices_response_YYYYMMDD_HHMMSS.json`** — полный ответ API
3. **Google Sheets** — обновленная таблица с данными

### Обработка ошибок
- **Валидация структуры** — остановка при неверной структуре данных
- **Ошибки записи** — логирование с продолжением выполнения
- **Ошибки валидации** — логирование с продолжением выполнения
- **Общие ошибки** — полное логирование с traceback

### Статистика выполнения
Функция выводит подробную статистику:
- Общее количество товаров
- Количество страниц и эффективность пагинации
- Распределение по категориям и брендам
- Статистика по обработанным данным
- Результаты валидации целостности

### Интеграция с другими модулями
- **API клиент** — `WB/wb_api/discounts_prices/discounts_prices.py`
- **Валидатор структуры** — `WB/excel_actions/discounts_prices_ea/structure_validator.py`
- **Обработчик данных** — `WB/excel_actions/discounts_prices_ea/data_processor.py`
- **Google Writer** — `WB/excel_actions/discounts_prices_ea/google_writer.py`
- **Валидатор данных** — `WB/excel_actions/discounts_prices_ea/data_validator.py`

---

## Идеи для дальнейшего улучшения
- Флаг `--no-write` для пропуска записи в таблицу.
- Режим `--preflight`: только проверка доступа/структуры без пагинации и записи.
- Чекпоинт пагинации (продолжение с последнего `lastChangeDate` между запусками).
- Автодобавление недостающих складов в шапку (по подтверждению).


