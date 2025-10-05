# Only Wildberries — README

Краткий гид по проекту: что это, как запустить и где править настройки.

## Что это
Проект для интеграции с Wildberries API и Google Sheets:
- wb_api: клиенты API (Content, Warehouse Remains, Discounts-Prices)
- excel_actions: чтение/запись/валидация Google Sheets
- main_function: сценарии верхнего уровня (запуск процессов)

## Быстрый старт ⚙️
1) Python 3.11+ (macOS)
2) Создать и активировать окружение:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
3) Установить зависимости:
```bash
pip install -r requirements.txt
```

## Конфигурация 🔐
Все настройки и ключи в `api_keys.py`:
- `ACTIVE_USER`: текущий профиль (например, `NOSOV`)
- `WB_API_TOKEN`: токен WB для API (берётся из активного профиля)
- `GOOGLE_CREDENTIALS_INFO`: inline JSON сервис‑аккаунта Google
- `GOOGLE_SHEET_ID*`: идентификаторы целевых таблиц

Переключение профиля без правки файла:
```bash
ACTIVE_USER=KUSKOV python main_function/warehouse_remains_mf/warehouse_remains.py
```

## Запуск основных сценариев 🚀
- База артикулов (Content → Sheets):
```bash
python main_function/list_of_seller_articles_mf/list_of_seller_articles.py
```
- Остатки по складам (Warehouse Remains → Sheets + валидация):
```bash
python main_function/warehouse_remains_mf/warehouse_remains.py
```
- Discounts-Prices: клиент и экшены доступны, запускать при наличии актуального JWT/cookies.

## Архитектура (коротко)
- `main_function/*` → orchestration (шаги процесса)
- `wb_api/*` → HTTP‑клиенты WB API
- `excel_actions/*` → Google Sheets I/O и валидации
- `api_keys.py` → единый конфиг и профили

## Логи и ошибки
- Ошибки авторизации: проверьте `WB_API_TOKEN`/JWT/куки и активный профиль
- Rate limit WB: сценарии учитывают ожидания, при 429 выполняют паузы

## Безопасность
- Секреты не коммитим. Креды Google держим inline в `api_keys.py` (или используем внешний файл локально)
- Не хардкодим пути/ID: используем профиль и динамические переменные
