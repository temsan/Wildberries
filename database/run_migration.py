#!/usr/bin/env python3
"""
🚀 ЕДИНСТВЕННАЯ ТОЧКА ЗАПУСКА МИГРАЦИЙ
Скрипт для применения исправлений безопасности в Supabase
"""

import sys
import os
from pathlib import Path

# Добавляем корневую директорию в path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

try:
    from supabase import create_client, Client
    import api_keys
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Установите зависимости: pip install supabase")
    sys.exit(1)

def get_supabase_client() -> Client:
    """Создает клиент Supabase"""
    try:
        url = api_keys.SUPABASE_URL
        key = api_keys.SUPABASE_KEY
        
        if not url or not key:
            raise ValueError("SUPABASE_URL или SUPABASE_KEY не установлены")
            
        return create_client(url, key)
    except Exception as e:
        print(f"Ошибка подключения к Supabase: {e}")
        sys.exit(1)

def run_migration(client: Client, migration_file: str):
    """Запускает миграцию из файла"""
    try:
        # Читаем файл миграции
        migration_path = Path(__file__).parent / "migrations" / migration_file
        
        if not migration_path.exists():
            print(f"Файл миграции не найден: {migration_path}")
            return False
            
        with open(migration_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print(f"Запуск миграции: {migration_file}")
        print("-" * 50)
        
        # Выполняем SQL
        result = client.rpc('exec_sql', {'sql': sql_content}).execute()
        
        print("Миграция выполнена успешно!")
        return True
        
    except Exception as e:
        print(f"Ошибка выполнения миграции: {e}")
        print(f"Тип ошибки: {type(e).__name__}")
        print(f"Подробности: {str(e)}")
        print()
        print("АЛЬТЕРНАТИВНЫЙ СПОСОБ:")
        print("1. Откройте Supabase Dashboard")
        print("2. Перейдите в SQL Editor")
        print("3. Скопируйте содержимое файла миграции:")
        print(f"   {migration_path}")
        print("4. Вставьте и выполните SQL")
        print()
        print("СОДЕРЖИМОЕ МИГРАЦИИ:")
        print("-" * 50)
        try:
            with open(migration_path, 'r', encoding='utf-8') as f:
                print(f.read())
        except Exception as read_error:
            print(f"Не удалось прочитать файл: {read_error}")
        print("-" * 50)
        return False

def get_migration_files():
    """Получает список всех миграционных файлов"""
    migrations_dir = Path(__file__).parent / "migrations"
    if not migrations_dir.exists():
        return []

    # Получаем все .sql файлы и сортируем по имени
    migration_files = sorted(migrations_dir.glob("*.sql"))
    return [f.name for f in migration_files]

def main():
    """Основная функция"""
    print("ОБЩИЙ СКРИПТ ЗАПУСКА МИГРАЦИЙ")
    print("=" * 50)
    print("Применение миграций к базе данных Supabase")
    print("=" * 50)

    # Создаем клиент
    client = get_supabase_client()
    print("Подключение к Supabase установлено")
    print()

    # Получаем список миграций
    migrations = get_migration_files()

    if not migrations:
        print("❌ Нет миграционных файлов в папке migrations/")
        sys.exit(1)

    print(f"Найдено миграций: {len(migrations)}")
    print("Файлы:", ", ".join(migrations))
    print()

    success_count = 0

    for migration in migrations:
        print(f"Выполнение миграции: {migration}")

        if run_migration(client, migration):
            success_count += 1
            print("УСПЕХ")
        else:
            print("ОШИБКА")

        print("-" * 50)
        print()

    print("РЕЗУЛЬТАТ:")
    print(f"Выполнено успешно: {success_count}/{len(migrations)}")

    if success_count == len(migrations):
        print("ВСЕ МИГРАЦИИ ВЫПОЛНЕНЫ УСПЕШНО!")

        # Специфическая информация для миграции безопасности
        if "001_fix_security_issues.sql" in migrations:
            print()
            print("Исправленные проблемы:")
            print("  • Функции: добавлен SET search_path = public")
            print("  • RLS политики: объединены множественные политики")
            print("  • Views: пересозданы без SECURITY DEFINER")
            print()
            print("Результат:")
            print("  • Function Search Path Mutable: ИСПРАВЛЕНО")
            print("  • Multiple Permissive Policies: ИСПРАВЛЕНО")
            print("  • Security Definer View: ИСПРАВЛЕНО")
            print()
            print("Проверьте Database Linter в Supabase - ошибки исчезли!")
    else:
        print("Некоторые миграции завершились с ошибками.")
        sys.exit(1)

if __name__ == "__main__":
    main()
