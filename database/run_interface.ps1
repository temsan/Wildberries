Write-Host "🚀 Запуск веб-интерфейса WB API Dashboard..." -ForegroundColor Green
Write-Host "📱 Интерфейс откроется в браузере через несколько секунд" -ForegroundColor Cyan
Write-Host "🛑 Для остановки нажмите Ctrl+C" -ForegroundColor Yellow
Write-Host ""

try {
    # Активируем виртуальное окружение если оно существует
    $venvPath = Join-Path $PSScriptRoot ".venv\Scripts\Activate.ps1"
    if (Test-Path $venvPath) {
        Write-Host "🔧 Активация виртуального окружения..." -ForegroundColor Blue
        & $venvPath
        python -m streamlit run (Join-Path $PSScriptRoot "web_interface.py")
    } else {
        Write-Host "⚠️  Виртуальное окружение не найдено, используем системный Python" -ForegroundColor Yellow
        python -m streamlit run (Join-Path $PSScriptRoot "web_interface.py")
    }
} catch {
    Write-Host "❌ Ошибка запуска: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "💡 Попробуйте запустить вручную: streamlit run database/web_interface.py" -ForegroundColor Gray
}

Write-Host ""
Write-Host "👋 Интерфейс остановлен" -ForegroundColor Green
Read-Host "Нажмите Enter для выхода"
