@echo off
echo 🚀 Запуск веб-интерфейса WB API Dashboard...
echo.

REM Переходим в папку database
cd /d "%~dp0database"

REM Проверяем наличие виртуального окружения
if exist ".venv\Scripts\activate.bat" (
    echo 🔧 Активация виртуального окружения...
    call .venv\Scripts\activate.bat
    python -m streamlit run web_interface.py
) else (
    echo ⚠️  Виртуальное окружение не найдено
    echo 💡 Сначала создайте окружение: python -m venv .venv
    echo    Затем установите зависимости: .venv\Scripts\activate ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo 👋 Интерфейс остановлен
pause
