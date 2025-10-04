# 🚀 Запуск веб-интерфейса WB API Dashboard

## Способы запуска

### 1️⃣ Через Python (автозапуск)
```bash
python database/web_interface.py
```

### 2️⃣ Через виртуальное окружение + Streamlit
```bash
.venv\Scripts\activate && python -m streamlit run database/web_interface.py
```

### 3️⃣ Через Batch файл (Windows)
```bash
database\run_interface.bat
```

### 4️⃣ Через PowerShell скрипт (Windows)
```powershell
database\run_interface.ps1
```

### 5️⃣ Через Bash скрипт (Linux/Mac/WSL)
```bash
chmod +x database/run_interface.sh
database/run_interface.sh
```

---

## 🎯 Рекомендуемый способ

**Для Windows (самый простой):**
```bash
database\run_interface.bat
```

**Для Linux/Mac/WSL:**
```bash
chmod +x database/run_interface.sh
./database/run_interface.sh
```

---

## 🔧 Что происходит при запуске

1. ✅ **Автоматическая активация** виртуального окружения `.venv`
2. ✅ **Запуск Streamlit сервера** без предупреждений
3. ✅ **Открытие браузера** на `http://localhost:8501`
4. ✅ **Чистая консоль** без ошибок ScriptRunContext

---

## 🌐 Адрес в браузере

**http://localhost:8501**

---

## 🛑 Остановка

- **Ctrl+C** в терминале
- Или закройте терминал

---

## 💡 Если не работает

### Проверьте виртуальное окружение:
```bash
# Убедитесь что зависимости установлены
.venv\Scripts\activate && pip list | grep streamlit
```

### Если нет виртуального окружения:
```bash
# Создайте и активируйте
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Если браузер не открывается:
Вручную откройте: **http://localhost:8501**

---

## 🎉 Готово!

После запуска увидите интерфейс с:
- 📊 Dashboard с метриками
- 🔄 Синхронизация данных из WB API
- 📦 Управление товарами
- 💰 Управление ценами
- 📝 Логи операций
- ⚙️ Настройки БД

**Приятной работы! 🚀**

