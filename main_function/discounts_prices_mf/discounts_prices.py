"""
Main-скрипт для получения данных о товарах со скидками через discounts-prices API.

Что делает:
1) Получает ВСЕ товары через WBDiscountsPricesClient (все страницы)
2) Валидирует структуру данных
3) Обрабатывает данные для отчета (цены, скидки, СПП)
4) Анализирует статистику пагинации и категорий
5) Записывает данные в Google таблицу (настройки в google_writer.py)
6) Проверяет целостность данных (сравнивает API с таблицей)
7) Логирует весь процесс

НАСТРОЙКИ GOOGLE ТАБЛИЦЫ:
- Находятся в excel_actions/discounts_prices_ea/google_writer.py
- sheet_name, article_search_range, start_row

ВАЛИДАЦИЯ ДАННЫХ:
- Сравнивает данные из API с данными в Google таблице
- Проверяет все поля: prices, discount, discountedPrices, etc.
- Выводит детальный отчет о несоответствиях

Запуск:
  python3 WB/main_function/discounts_prices_mf/discounts_prices.py
  python3 WB/main_function/discounts_prices_mf/discounts_prices.py --page-size 100
  python3 WB/main_function/discounts_prices_mf/discounts_prices.py --sleep-seconds 0.5
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import importlib.util

# Настройка логирования
def setup_logging():
    """Настройка системы логирования."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('discounts_prices.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

def import_discounts_client():
    """Динамический импорт WBDiscountsPricesClient."""
    BASE_DIR = Path(__file__).resolve().parents[2]
    discounts_path = BASE_DIR / 'wb_api' / 'discounts_prices' / 'discounts_prices.py'

    spec = importlib.util.spec_from_file_location("discounts_prices", str(discounts_path))
    discounts_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(discounts_module)

    return discounts_module.WBDiscountsPricesClient


def import_api_keys():
    """Импорт настроек из api_keys.py."""
    BASE_DIR = Path(__file__).resolve().parents[2]
    api_keys_path = BASE_DIR / 'api_keys.py'

    spec = importlib.util.spec_from_file_location("api_keys", str(api_keys_path))
    api_keys_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api_keys_module)

    return api_keys_module

def import_structure_validator():
    """Динамический импорт структуры валидатора."""
    BASE_DIR = Path(__file__).resolve().parents[2]
    validator_path = BASE_DIR / 'excel_actions' / 'discounts_prices_ea' / 'structure_validator.py'
    
    spec = importlib.util.spec_from_file_location("structure_validator", str(validator_path))
    validator_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator_module)
    
    return validator_module.check_and_validate_structure

def import_data_processor():
    """Динамический импорт обработчика данных."""
    BASE_DIR = Path(__file__).resolve().parents[2]
    processor_path = BASE_DIR / 'excel_actions' / 'discounts_prices_ea' / 'data_processor.py'
    
    spec = importlib.util.spec_from_file_location("data_processor", str(processor_path))
    processor_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(processor_module)
    
    return processor_module.process_discounts_data, processor_module.get_report_summary

def analyze_goods_data(all_goods: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Анализирует данные о товарах и возвращает статистику."""
    total_goods = len(all_goods)
    
    # Анализируем размерность страниц
    page_size = 50
    total_pages = (total_goods + page_size - 1) // page_size
    
    # Анализируем классы товаров (subject)
    subjects = {}
    brands = {}
    
    for good in all_goods:
        # Подсчитываем классы товаров
        subject = good.get('subject', 'Не указан')
        subjects[subject] = subjects.get(subject, 0) + 1
        
        # Подсчитываем бренды
        brand = good.get('brand', 'Не указан')
        brands[brand] = brands.get(brand, 0) + 1
    
    # Сортируем по количеству
    subjects_sorted = sorted(subjects.items(), key=lambda x: x[1], reverse=True)
    brands_sorted = sorted(brands.items(), key=lambda x: x[1], reverse=True)
    
    analysis = {
        "pagination": {
            "page_size": page_size,
            "total_pages": total_pages,
            "total_goods": total_goods,
            "efficiency": total_goods / total_pages if total_pages > 0 else 0
        },
        "subjects": {
            "count": len(subjects),
            "data": subjects_sorted
        },
        "brands": {
            "count": len(brands),
            "data": brands_sorted
        }
    }
    
    return analysis

def print_analysis_report(analysis: Dict[str, Any]):
    """Выводит отчет по анализу данных."""
    logger = logging.getLogger(__name__)
    
    pagination = analysis["pagination"]
    subjects = analysis["subjects"]
    brands = analysis["brands"]
    
    logger.info(f"📂 НАЙДЕННЫЕ КЛАССЫ ТОВАРОВ ({subjects['count']}):")
    logger.info("-" * 40)
    for subject, count in subjects["data"]:
        percentage = (count / pagination['total_goods']) * 100
        logger.info(f"  • {subject}: {count} товаров ({percentage:.1f}%)")
    
    logger.info(f"\n🏷️  БРЕНДЫ ({brands['count']}):")
    logger.info("-" * 40)
    for brand, count in brands["data"]:
        percentage = (count / pagination['total_goods']) * 100
        logger.info(f"  • {brand}: {count} товаров ({percentage:.1f}%)")
    
    logger.info(f"\n✅ АНАЛИЗ УСПЕШНО ЗАВЕРШЕН!")


def print_processed_data_report(processed_data: List[Dict[str, Any]], summary: Dict[str, Any]):
    """Выводит детальный отчет по обработанным данным."""
    logger = logging.getLogger(__name__)
    
    print("\n" + "=" * 80)
    print("📊 ОТЧЕТ ПО ВЫПОЛНЕНИЮ")
    print("=" * 80)
    
    # Подсчитываем статистику
    total_articles = len(processed_data)
    articles_with_spp = sum(1 for item in processed_data if item['discountOnSite'] > 0)
    articles_with_competitive_price = sum(1 for item in processed_data if item['isCompetitivePrice'] == True)
    articles_with_promotions = sum(1 for item in processed_data if item['hasPromotions'] == True)
    
    print(f"📦 Артикулов обработано: {total_articles}")
    print(f"🏷️ Имеют СПП больше 0: {articles_with_spp}")
    print(f"💰 Статус isCompetitivePrice True: {articles_with_competitive_price}")
    print(f"🎯 Статус hasPromotions True: {articles_with_promotions}")
    
    print("\n" + "=" * 80)
    print("📄 ПРИМЕРЫ ПО ПЕРВЫМ ТРЕМ АРТИКУЛАМ")
    print("=" * 80)
    
    # Показываем первые 3 товара
    for i, item in enumerate(processed_data[:3]):
        print(f"\n🔹 Артикул {i+1}:")
        print(f"   nmID: {item['nmID']}")
        print(f"   vendorCode: {item['vendorCode']}")
        print(f"   brand: {item['brand']}")
        print(f"   subject: {item['subject']}")
        print(f"   prices: {item['prices']}")
        print(f"   discountedPrices: {item['discountedPrices']}")
        print(f"   discount: {item['discount']}%")
        print(f"   discountOnSite: {item['discountOnSite']}%")
        print(f"   priceafterSPP: {item['priceafterSPP']}")
        print(f"   competitivePrice: {item['competitivePrice']}")
        print(f"   isCompetitivePrice: {item['isCompetitivePrice']}")
        print(f"   hasPromotions: {item['hasPromotions']}")
    
    print("\n✅ ОТЧЕТ ПО ВЫПОЛНЕНИЮ ЗАВЕРШЕН!")

def save_json_response(all_goods: List[Dict[str, Any]], analysis: Dict[str, Any]) -> str:
    """Сохраняет JSON ответ в текущую папку."""
    logger = logging.getLogger(__name__)
    
    # Создаем полную структуру ответа
    response_data = {
        "data": {"listGoods": all_goods},
        "error": False,
        "errorText": "",
        "analysis": analysis,
        "metadata": {
            "retrieved_at": datetime.now().isoformat(),
            "total_goods": len(all_goods),
            "api_endpoint": "https://discounts-prices.wildberries.ru/ns/dp-api/discounts-prices/suppliers/api/v1/list/goods/filter"
        }
    }
    
    # Сохраняем в текущую папку
    output_path = Path.cwd() / f"discounts_prices_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(response_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"💾 JSON ответ сохранен: {output_path}")
    logger.info(f"📁 Размер файла: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    return str(output_path)

def main():
    """Основная функция."""
    parser = argparse.ArgumentParser(description='Получение данных о товарах со скидками')
    parser.add_argument('--page-size', type=int, default=50, help='Размер страницы (по умолчанию 50)')
    parser.add_argument('--sleep-seconds', type=float, default=1.0, help='Задержка между запросами (по умолчанию 1.0)')


    args = parser.parse_args()

    # Настройка логирования
    logger = setup_logging()

    logger.info("🚀 ЗАПУСК MAIN ФУНКЦИИ DISCOUNTS_PRICES")

    try:
        # Импортируем настройки из api_keys.py
        api_keys = import_api_keys()

        # Отладочная информация - проверяем, что credentials загружены
        logger.info(f"🔑 Токен загружен: {api_keys.AUTHORIZEV3_TOKEN[:50]}...")
        logger.info(f"🍪 Куки загружены: {len(api_keys.COOKIES)} символов")
        logger.info(f"🌐 User-Agent загружен: {api_keys.USER_AGENT[:50]}...")
        logger.info(f"📊 Используемая таблица: {api_keys.GOOGLE_SHEET_ID_UNIT_ECONOMICS}")
        logger.info(f"📋 Название листа для поиска: Юнитка")

        # Импортируем клиент
        WBDiscountsPricesClient = import_discounts_client()

        # Создаем клиент с параметрами из api_keys
        client = WBDiscountsPricesClient(
            authorizev3_token=api_keys.AUTHORIZEV3_TOKEN,
            cookies=api_keys.COOKIES,
            user_agent=api_keys.USER_AGENT
        )

        # Получаем все товары (всегда все страницы)
        logger.info(f"⚙️  Параметры: page_size={args.page_size}, sleep_seconds={args.sleep_seconds}")
        logger.info("🔄 Обрабатываем ВСЕ страницы товаров...")

        all_goods = client.iterate_all_goods(
            page_size=args.page_size,
            sleep_seconds=args.sleep_seconds,
            max_pages=None  # Всегда обрабатываем все страницы
        )
        
        # Валидируем структуру данных
        logger.info("🔍 Валидация структуры данных...")
        validate_structure = import_structure_validator()
        
        # Формируем данные в формате API для валидации
        response_data = {
            "data": {
                "listGoods": all_goods
            },
            "error": False,
            "errorText": "",
            "analysis": {},
            "metadata": {
                "total_goods": len(all_goods),
                "api_endpoint": "https://discounts-prices.wildberries.ru/ns/dp-api/discounts-prices/suppliers/api/v1/list/goods/filter"
            }
        }
        
        # Запускаем валидацию
        is_valid = validate_structure(response_data)
        
        if not is_valid:
            logger.error("❌ Валидация структуры не прошла. Выполнение остановлено.")
            return 1
        
        logger.info("✅ Валидация структуры прошла успешно")
        
        # Обрабатываем данные для отчета
        logger.info("🔄 Обрабатываем данные для отчета...")
        process_data, get_summary = import_data_processor()
        
        processed_data = process_data(all_goods)
        summary = get_summary(processed_data)
        
        logger.info(f"✅ Обработано {summary['total_items']} товаров")
        logger.info(f"💰 С конкурентной ценой: {summary['items_with_competitive_price']} ({summary['competitive_price_coverage']:.1f}%)")
        logger.info(f"🎯 С промоакциями: {summary['items_with_promotions']} ({summary['promotions_coverage']:.1f}%)")
        logger.info(f"🏷️ С СПП: {summary['items_with_spp']} ({summary['spp_coverage']:.1f}%)")
        
        # Анализируем данные (оригинальный анализ)
        analysis = analyze_goods_data(all_goods)
        
        # Выводим отчет
        print_analysis_report(analysis)
        
        # По просьбе пользователя: не выводить подробный отчет по выполнению
        
        # Записываем данные в Google таблицу
        logger.info("🔄 Записываем данные в Google таблицу...")
        try:
            # Импортируем google_writer из excel_actions
            import sys
            from pathlib import Path
            excel_actions_path = Path(__file__).parent.parent.parent / "excel_actions" / "discounts_prices_ea"
            sys.path.append(str(excel_actions_path))

            from google_writer import write_discounts_prices_to_sheet  # type: ignore

            # Передаем параметры из api_keys - используем таблицу UNIT_ECONOMICS для discounts_prices
            result = write_discounts_prices_to_sheet(
                processed_data,
                spreadsheet_id=api_keys.GOOGLE_SHEET_ID_UNIT_ECONOMICS,
                credentials_info=api_keys.GOOGLE_CREDENTIALS_INFO
            )

            logger.info(f"✅ Запись в Google таблицу завершена!")
            logger.info(f"   • Обработано артикулов: {result['processed_rows']}")
            logger.info(f"   • Артикулов не найдено: {result['not_found_articles']}")

        except Exception as e:
            logger.warning(f"⚠️ Ошибка записи в Google таблицу (лист не найден или нет доступа): {e}")
            logger.info("📋 Основная функциональность работает - данные из WB API получены и обработаны")
            import traceback
            logger.info(f"Детали ошибки: {traceback.format_exc()}")
        
        # Проверяем целостность данных
        logger.info("🔍 Проверяем целостность данных...")
        try:
            from data_validator import validate_data_integrity, print_validation_report  # type: ignore

            # Передаем параметры из api_keys для валидации - используем таблицу UNIT_ECONOMICS для discounts_prices
            validation_result = validate_data_integrity(
                processed_data,
                spreadsheet_id=api_keys.GOOGLE_SHEET_ID_UNIT_ECONOMICS,
                credentials_info=api_keys.GOOGLE_CREDENTIALS_INFO
            )
            print_validation_report(validation_result)

            if validation_result['validation_passed']:
                logger.info("✅ Валидация данных прошла успешно!")
            else:
                logger.warning("⚠️ Валидация данных выявила несоответствия!")

        except Exception as e:
            logger.warning(f"⚠️ Ошибка валидации данных (лист не найден или нет доступа): {e}")
            logger.info("📋 Основная функциональность работает - данные из WB API получены и обработаны")
            import traceback
            logger.info(f"Детали ошибки: {traceback.format_exc()}")
        
        logger.info("\n🎉 MAIN ФУНКЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Ошибка в main функции: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
