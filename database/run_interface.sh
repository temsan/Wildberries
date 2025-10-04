#!/bin/bash

echo "🚀 Запуск веб-интерфейса WB API Dashboard..."
echo "📱 Интерфейс откроется в браузере через несколько секунд"
echo "🛑 Для остановки нажмите Ctrl+C"
echo

# Активируем виртуальное окружение если оно существует
VENV_PATH="$(dirname "$0")/.venv/bin/activate"
if [ -f "$VENV_PATH" ]; then
    echo "🔧 Активация виртуального окружения..."
    source "$VENV_PATH"
    python -m streamlit run "$(dirname "$0")/web_interface.py"
else
    echo "⚠️  Виртуальное окружение не найдено, используем системный Python"
    python -m streamlit run "$(dirname "$0")/web_interface.py"
fi

echo
echo "👋 Интерфейс остановлен"
