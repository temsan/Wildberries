#!/usr/bin/env python3
"""
Интеграция с Google Sheets для чтения данных из таблицы Макара
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

# Добавляем корневую директорию в path
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    print("⚠️  Google Sheets API не установлен. Установите: pip install google-api-python-client google-auth")


class GoogleSheetsReader:
    """Читатель данных из Google Sheets"""
    
    def __init__(self, credentials_file: Optional[str] = None):
        """
        Инициализация читателя Google Sheets.
        
        Args:
            credentials_file: Путь к файлу учетных данных (service account)
        """
        if not GOOGLE_SHEETS_AVAILABLE:
            raise ImportError("Google Sheets API не установлен")
        
        self.credentials_file = credentials_file or self._find_credentials_file()
        self.service = None
        self._authenticate()
    
    def _find_credentials_file(self) -> Optional[str]:
        """Ищет файл учетных данных Google Sheets"""
        possible_paths = [
            BASE_DIR / "credentials.json",
            BASE_DIR / "google_credentials.json", 
            BASE_DIR / "service_account.json",
            BASE_DIR / "database" / "credentials.json",
            BASE_DIR / "database" / "google_credentials.json"
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        return None
    
    def _authenticate(self):
        """Аутентификация в Google Sheets API"""
        if not self.credentials_file:
            raise FileNotFoundError(
                "Не найден файл учетных данных Google Sheets. "
                "Разместите файл credentials.json в корне проекта."
            )
        
        try:
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_file, scopes=SCOPES
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            print(f"✅ Аутентификация Google Sheets успешна")
        except Exception as e:
            raise Exception(f"Ошибка аутентификации Google Sheets: {e}")
    
    def read_spreadsheet(self, spreadsheet_id: str, range_name: str) -> List[List[str]]:
        """
        Читает данные из Google Sheets.
        
        Args:
            spreadsheet_id: ID таблицы Google Sheets
            range_name: Диапазон ячеек (например, 'Sheet1!A1:Z100')
            
        Returns:
            Список строк с данными
        """
        try:
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            print(f"📊 Прочитано {len(values)} строк из Google Sheets")
            return values
            
        except HttpError as e:
            print(f"❌ Ошибка чтения Google Sheets: {e}")
            return []
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            return []
    
    def read_makar_table(self, spreadsheet_id: str = None) -> Dict[str, Any]:
        """
        Читает таблицу Макара с конфигурацией артикулов.
        
        Args:
            spreadsheet_id: ID таблицы (если не указан, используется из URL)
            
        Returns:
            Структурированные данные таблицы
        """
        if not spreadsheet_id:
            # ID из URL Макара: 1Aufum97SY2fChBKNyzP0tslUYbCQ6cCd41EkoEo05SM
            spreadsheet_id = "1Aufum97SY2fChBKNyzP0tslUYbCQ6cCd41EkoEo05SM"
        
        print(f"📋 Читаем таблицу Макара: {spreadsheet_id}")
        
        # Читаем данные из первого листа
        data = self.read_spreadsheet(spreadsheet_id, 'A1:Z100')
        
        if not data:
            return {'error': 'Не удалось прочитать данные из таблицы'}
        
        # Парсим структуру таблицы
        result = {
            'spreadsheet_id': spreadsheet_id,
            'total_rows': len(data),
            'headers': data[0] if data else [],
            'raw_data': data,
            'parsed_data': self._parse_makar_table(data)
        }
        
        return result
    
    def _parse_makar_table(self, data: List[List[str]]) -> Dict[str, Any]:
        """
        Парсит таблицу Макара в структурированный формат.
        
        Args:
            data: Сырые данные из Google Sheets
            
        Returns:
            Структурированные данные
        """
        if len(data) < 2:
            return {'error': 'Недостаточно данных для парсинга'}
        
        headers = data[0]
        rows = data[1:]
        
        # Определяем структуру на основе заголовков
        structure = {
            'columns': headers,
            'entities': [],
            'time_series': [],
            'simple_update': []
        }
        
        # Анализируем заголовки для определения типа хранения
        for header in headers:
            if header:
                header_lower = header.lower()
                if any(keyword in header_lower for keyword in ['конверсии', 'заказы', 'продажи', 'остатки', 'себестоимость', 'рекламные']):
                    structure['time_series'].append(header)
                else:
                    structure['simple_update'].append(header)
        
        # Парсим данные по строкам
        for i, row in enumerate(rows):
            if not row or not row[0]:  # Пропускаем пустые строки
                continue
            
            entity = {
                'row_index': i + 2,  # +2 потому что начинаем с 1 и пропускаем заголовок
                'data': {}
            }
            
            # Заполняем данные по столбцам
            for j, value in enumerate(row):
                if j < len(headers) and headers[j]:
                    entity['data'][headers[j]] = value
            
            structure['entities'].append(entity)
        
        return structure
    
    def export_to_json(self, data: Dict[str, Any], output_file: str) -> bool:
        """
        Экспортирует данные в JSON файл.
        
        Args:
            data: Данные для экспорта
            output_file: Путь к выходному файлу
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            output_path = BASE_DIR / "exports" / output_file
            output_path.parent.mkdir(exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"✅ Данные экспортированы в {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка экспорта: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Тестирует подключение к Google Sheets"""
        try:
            # Пробуем прочитать одну ячейку из таблицы Макара
            test_data = self.read_spreadsheet(
                "1Aufum97SY2fChBKNyzP0tslUYbCQ6cCd41EkoEo05SM", 
                'A1:A1'
            )
            return len(test_data) > 0
        except Exception as e:
            print(f"❌ Ошибка тестирования подключения: {e}")
            return False


def main():
    """Основная функция для тестирования"""
    print("🧪 ТЕСТ ЧТЕНИЯ ТАБЛИЦЫ МАКАРА")
    print("=" * 50)
    
    try:
        # Создаем читатель
        reader = GoogleSheetsReader()
        
        # Тестируем подключение
        if not reader.test_connection():
            print("❌ Не удалось подключиться к Google Sheets")
            return
        
        print("✅ Подключение к Google Sheets успешно")
        
        # Читаем таблицу Макара
        print("\n📋 Читаем таблицу Макара...")
        data = reader.read_makar_table()
        
        if 'error' in data:
            print(f"❌ Ошибка: {data['error']}")
            return
        
        # Выводим статистику
        print(f"\n📊 Статистика:")
        print(f"   • Всего строк: {data['total_rows']}")
        print(f"   • Заголовки: {len(data['headers'])}")
        print(f"   • Сущностей: {len(data['parsed_data']['entities'])}")
        
        # Показываем заголовки
        print(f"\n📋 Заголовки таблицы:")
        for i, header in enumerate(data['headers']):
            print(f"   {i+1}. {header}")
        
        # Показываем тип хранения
        parsed = data['parsed_data']
        print(f"\n🔄 Временные ряды:")
        for item in parsed['time_series']:
            print(f"   • {item}")
        
        print(f"\n✅ Простое обновление:")
        for item in parsed['simple_update']:
            print(f"   • {item}")
        
        # Показываем примеры данных
        if parsed['entities']:
            print(f"\n📦 Примеры сущностей:")
            for i, entity in enumerate(parsed['entities'][:3]):
                print(f"   {i+1}. Строка {entity['row_index']}:")
                for key, value in entity['data'].items():
                    if value:
                        print(f"      • {key}: {value}")
        
        # Экспортируем данные
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_file = f"makar_table_{timestamp}.json"
        reader.export_to_json(data, export_file)
        
        print(f"\n✅ Тест завершен успешно!")
        
    except ImportError as e:
        print(f"❌ {e}")
        print("💡 Установите зависимости: pip install google-api-python-client google-auth")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    main()
