# ============================================================================
# ПРИМЕР КОНФИГУРАЦИИ ДЛЯ SUPABASE
# ============================================================================
# Скопируйте эти строки в ваш файл api_keys.py (в корне проекта)
# и замените значения на свои из Supabase Dashboard

# Supabase credentials
# Получить в: Dashboard → Settings → API
SUPABASE_URL = "https://your-project.supabase.co"  # Project URL
SUPABASE_KEY = "your-anon-public-key-here"  # anon public key (длинный JWT токен)

# ============================================================================
# ИНСТРУКЦИЯ
# ============================================================================
# 1. Создайте проект на https://supabase.com
# 2. Скопируйте URL и anon key из Settings → API
# 3. Добавьте эти переменные в конец вашего api_keys.py
# 4. Запустите schema.sql через SQL Editor в Supabase Dashboard
# 5. Проверьте подключение: python database/db_client.py

