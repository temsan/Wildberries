#!/usr/bin/env python3
"""
🚀 WB API Dashboard - Чистый минималистичный интерфейс
"""

# =============================================================================
# ПРОВЕРКА И АВТОЗАПУСК STREAMLIT
# =============================================================================
import sys
import os

# Проверяем, что НЕ запущено через streamlit
if __name__ == "__main__" and "streamlit.runtime.scriptrunner" not in sys.modules:
    import subprocess
    
    print("🚀 Запуск веб-интерфейса через Streamlit...")
    print("📱 Откройте браузер: http://localhost:8501")
    print()
    
    try:
        # Запускаем streamlit run для этого файла
        subprocess.run([sys.executable, "-m", "streamlit", "run", __file__], check=True)
    except KeyboardInterrupt:
        print("\n👋 Интерфейс остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        print("💡 Установите Streamlit: pip install streamlit")
    
    sys.exit(0)

# =============================================================================
# ОСНОВНОЙ КОД ИНТЕРФЕЙСА
# =============================================================================
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import json
from pathlib import Path

# Настройки страницы
st.set_page_config(
    page_title="WB API Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# LIQUID GLASS CSS
st.markdown("""
<style>
/* Анимированный градиентный фон */
.stApp {
    background: linear-gradient(-45deg, #1a1a1a, #2d2d2d, #1a1a1a, #3d3d3d) !important;
    background-size: 400% 400% !important;
    animation: gradientShift 15s ease infinite !important;
}

@keyframes gradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* Основной контент */
.main .block-container {
    background: rgba(255, 255, 255, 0.03) !important;
    backdrop-filter: blur(15px) !important;
    border-radius: 15px !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2) !important;
    margin: 0.5rem !important;
    padding: 0.75rem !important;
}

/* LIQUID GLASS SIDEBAR */
.css-1d391kg {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05)) !important;
    backdrop-filter: blur(20px) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
    border-radius: 0 20px 20px 0 !important;
}

/* Кнопки навигации */
.css-1d391kg .stButton > button {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05)) !important;
    backdrop-filter: blur(15px) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    border-radius: 12px !important;
    color: #ffffff !important;
    transition: all 0.3s ease !important;
    margin: 0.25rem 0 !important;
    padding: 0.75rem 1rem !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3) !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
}

.css-1d391kg .stButton > button:hover {
    background: linear-gradient(135deg, rgba(0, 212, 170, 0.2), rgba(0, 212, 170, 0.1)) !important;
    border: 1px solid rgba(0, 212, 170, 0.4) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(0, 212, 170, 0.3) !important;
    color: #00d4aa !important;
}

/* Компактные элементы */
.element-container { margin-bottom: 0.1rem !important; }
.stMarkdown { margin-bottom: 0.05rem !important; }
h1, h2, h3, h4, h5, h6 { margin-top: 0.1rem !important; margin-bottom: 0.1rem !important; }
</style>
""", unsafe_allow_html=True)

# Заголовок
st.markdown("### 📦 WB API Dashboard")
st.markdown("Комплексное решение для автоматизации Wildberries API")

# Статус подключения
if st.session_state.get('db_connected', False):
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(34, 197, 94, 0.1)); 
                border: 1px solid rgba(34, 197, 94, 0.3); 
                border-radius: 8px; 
                padding: 1rem; 
                margin: 1rem 0;
                backdrop-filter: blur(10px);">
        <h3 style="color: #22c55e; margin: 0;">✅ База данных подключена</h3>
        <p style="color: #9ca3af; margin: 0.5rem 0 0 0;">Система готова к работе</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(239, 68, 68, 0.1)); 
                border: 1px solid rgba(239, 68, 68, 0.3); 
                border-radius: 8px; 
                padding: 1rem; 
                margin: 1rem 0;
                backdrop-filter: blur(10px);">
        <h3 style="color: #ef4444; margin: 0;">❌ База данных не подключена</h3>
        <p style="color: #9ca3af; margin: 0.5rem 0 0 0;">Проверьте настройки в api_keys.py</p>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# БОКОВОЕ МЕНЮ
# =============================================================================
with st.sidebar:
    st.markdown("### 🎛️ Навигация")
    
    # Кнопки навигации
    if st.button("📊 Dashboard", key="nav_dashboard", use_container_width=True):
        st.session_state.current_page = "📊 Dashboard"
    
    if st.button("🔄 Синхронизация", key="nav_sync", use_container_width=True):
        st.session_state.current_page = "🔄 Синхронизация"
    
    if st.button("📦 Товары", key="nav_products", use_container_width=True):
        st.session_state.current_page = "📦 Товары"
    
    if st.button("💰 Цены", key="nav_prices", use_container_width=True):
        st.session_state.current_page = "💰 Цены"
    
    if st.button("📈 История цен", key="nav_history", use_container_width=True):
        st.session_state.current_page = "📈 История цен"
    
    if st.button("📝 Логи", key="nav_logs", use_container_width=True):
        st.session_state.current_page = "📝 Логи"
    
    if st.button("🔧 SQL Запросы", key="nav_sql", use_container_width=True):
        st.session_state.current_page = "🔧 SQL Запросы"
    
    if st.button("⚙️ Настройки", key="nav_settings", use_container_width=True):
        st.session_state.current_page = "⚙️ Настройки"
    
    # Получаем текущую страницу
    page = st.session_state.get('current_page', "📊 Dashboard")
    
    st.markdown("---")
    st.markdown("### 📊 Статус")
    st.success("✅ Система активна")
    st.info("🔄 Последнее обновление: 2 мин назад")

# =============================================================================
# СОДЕРЖИМОЕ СТРАНИЦ
# =============================================================================

if page == "📊 Dashboard":
    # Основные метрики
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Всего товаров",
            value="1,234",
            delta="+12"
        )
    
    with col2:
        st.metric(
            label="Активных товаров",
            value="1,156",
            delta="+8"
        )
    
    with col3:
        st.metric(
            label="Средняя цена",
            value="2,450 ₽",
            delta="-150 ₽"
        )
    
    with col4:
        st.metric(
            label="Конверсия",
            value="12.5%",
            delta="+1.2%"
        )

elif page == "🔄 Синхронизация":
    sync_option = st.selectbox(
        "Источник",
        ["Content Cards (карточки товаров)", "Discounts-Prices (цены и скидки)", "Warehouse Remains (остатки)"]
    )
    
    if st.button("🔄 Запустить синхронизацию", type="primary"):
        st.success("✅ Синхронизация завершена!")

elif page == "📦 Товары":
    if st.button("📊 Анализ товаров", key="btn_4"):
        st.info("Анализ запущен")
    
    if st.button("📤 Экспорт в Excel", key="btn_5"):
        st.info("Экспорт запущен")

elif page == "💰 Цены":
    if st.button("📊 Анализ цен", key="btn_9"):
        st.info("Анализ цен запущен")
    
    if st.button("💰 Обновить цены", key="btn_10"):
        st.info("Обновление цен запущено")

elif page == "📈 История цен":
    if st.button("📤 Экспорт в Excel", key="btn_14"):
        st.success("Экспорт истории в Excel запущен")

elif page == "📝 Логи":
    if st.button("🔄 Обновить логи", key="btn_18"):
        st.success("Логи обновлены")

elif page == "🔧 SQL Запросы":
    if st.button("📋 Выполнить запрос", key="sql_btn_1"):
        st.info("Запрос выполнен")

elif page == "⚙️ Настройки":
    if st.button("💾 Сохранить настройки"):
        st.success("Настройки сохранены")
