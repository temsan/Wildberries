#!/usr/bin/env python3
"""
Проверка структуры таблицы Макара для понимания организации данных
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Добавляем корневую директорию в path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False


def check_table_structure():
    """Проверяет структуру таблицы Макара"""
    print("🔍 ПРОВЕРКА СТРУКТУРЫ ТАБЛИЦЫ МАКАРА")
    print("=" * 60)
    print("Таблица: https://docs.google.com/spreadsheets/d/1Aufum97SY2fChBKNyzP0tslUYbCQ6cCd41EkoEo05SM/edit")
    print("=" * 60)
    
    if not GOOGLE_SHEETS_AVAILABLE:
        print("❌ Google Sheets API не установлен")
        print("💡 Установите: pip install google-api-python-client google-auth")
        return
    
    # ID таблицы Макара
    SPREADSHEET_ID = "1Aufum97SY2fChBKNyzP0tslUYbCQ6cCd41EkoEo05SM"
    
    try:
        # Проверяем наличие файла учетных данных
        credentials_path = BASE_DIR / "credentials.json"
        if not credentials_path.exists():
            print("❌ Файл credentials.json не найден")
            print("💡 Создайте Service Account и поместите файл в корень проекта")
            print("📖 Инструкции: https://developers.google.com/sheets/api/quickstart/python")
            return
        
        # Аутентификация
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        credentials = service_account.Credentials.from_service_account_file(
            str(credentials_path), scopes=SCOPES
        )
        service = build('sheets', 'v4', credentials=credentials)
        
        print("✅ Подключение к Google Sheets успешно")
        
        # Читаем заголовки и первые несколько строк
        print("\n📋 Читаем структуру таблицы...")
        
        # Получаем данные из диапазона A1:Z20 (заголовки + примеры)
        range_name = 'A1:Z20'
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            print("❌ Таблица пуста или недоступна")
            return
        
        print(f"✅ Прочитано {len(values)} строк")
        
        # Анализируем структуру
        analyze_table_structure(values)
        
    except HttpError as e:
        print(f"❌ Ошибка Google Sheets API: {e}")
        if "PERMISSION_DENIED" in str(e):
            print("💡 Проверьте:")
            print("   1. Файл credentials.json в корне проекта")
            print("   2. Service Account добавлен в таблицу")
            print("   3. Права доступа: Viewer")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


def analyze_table_structure(values: List[List[str]]):
    """Анализирует структуру таблицы"""
    print(f"\n📊 АНАЛИЗ СТРУКТУРЫ ТАБЛИЦЫ")
    print("-" * 40)
    
    # Заголовки (первая строка)
    headers = values[0] if values else []
    print(f"📋 Заголовки ({len(headers)} колонок):")
    for i, header in enumerate(headers):
        if header:
            print(f"   {i+1:2d}. {header}")
    
    # Анализируем типы данных по заголовкам
    print(f"\n🔍 АНАЛИЗ ПО ТИПУ ХРАНЕНИЯ:")
    
    time_series_columns = []
    simple_update_columns = []
    
    for header in headers:
        if not header:
            continue
            
        header_lower = header.lower()
        
        # Ключевые слова для временных рядов
        time_series_keywords = [
            'конверсии', 'заказы', 'продажи', 'остатки', 'себестоимость',
            'рекламные', 'кампании', 'отчет', 'история', 'динамика',
            'тренд', 'изменение', 'рост', 'снижение'
        ]
        
        # Ключевые слова для простого обновления
        simple_keywords = [
            'продукт', 'артикул', 'баркод', 'размер', 'название',
            'категория', 'бренд', 'описание', 'характеристика'
        ]
        
        if any(keyword in header_lower for keyword in time_series_keywords):
            time_series_columns.append(header)
        elif any(keyword in header_lower for keyword in simple_keywords):
            simple_update_columns.append(header)
        else:
            # Если не определили, добавляем в простые обновления
            simple_update_columns.append(header)
    
    print(f"\n🔄 ВРЕМЕННЫЕ РЯДЫ (нужна история изменений):")
    if time_series_columns:
        for col in time_series_columns:
            print(f"   • {col}")
    else:
        print("   (не найдено)")
    
    print(f"\n✅ ПРОСТОЕ ОБНОВЛЕНИЕ (текущее состояние):")
    if simple_update_columns:
        for col in simple_update_columns:
            print(f"   • {col}")
    else:
        print("   (не найдено)")
    
    # Показываем примеры данных
    if len(values) > 1:
        print(f"\n📦 ПРИМЕРЫ ДАННЫХ:")
        print("-" * 30)
        
        # Показываем первые 3 строки данных (пропускаем заголовок)
        for i, row in enumerate(values[1:4], 1):
            print(f"\nСтрока {i+1}:")
            for j, value in enumerate(row):
                if j < len(headers) and headers[j] and value:
                    print(f"   • {headers[j]}: {value}")
    
    # Рекомендации по структуре БД
    print(f"\n💡 РЕКОМЕНДАЦИИ ПО СТРУКТУРЕ БД:")
    print("-" * 40)
    
    if time_series_columns:
        print("📊 Таблицы с историей (временные ряды):")
        print("   CREATE TABLE metrics_history (")
        print("       id BIGSERIAL PRIMARY KEY,")
        print("       nm_id INTEGER,")
        print("       recorded_at TIMESTAMP,")
        for col in time_series_columns:
            col_name = col.lower().replace(' ', '_').replace('-', '_')
            print(f"       {col_name} DECIMAL(10,2),")
        print("   );")
        print()
    
    if simple_update_columns:
        print("📋 Таблицы простого обновления:")
        print("   CREATE TABLE products (")
        print("       id BIGSERIAL PRIMARY KEY,")
        print("       nm_id INTEGER UNIQUE,")
        for col in simple_update_columns:
            col_name = col.lower().replace(' ', '_').replace('-', '_')
            print(f"       {col_name} VARCHAR(255),")
        print("       updated_at TIMESTAMP DEFAULT NOW()")
        print("   );")


if __name__ == "__main__":
    check_table_structure()
