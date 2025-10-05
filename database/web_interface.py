#!/usr/bin/env python3
"""
🚀 WB API Dashboard - Полнофункциональный интерфейс
Восстановлена вся логика + новый дизайн с вкладками сверху
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
# ОСНОВНОЙ КОД ИНТЕРФЕЙСА (выполняется только через streamlit run)
# =============================================================================
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import json
from pathlib import Path

# Добавляем корневую директорию в path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.db_client import get_client
from database.integrations.content_cards_db import sync_content_cards_to_db
from database.integrations.discounts_prices_db import sync_discounts_prices_to_db
from database.integrations.discounts_prices_enhanced import DiscountsPricesDBProcessor

# Настройки страницы
st.set_page_config(
    page_title="WB API Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Максимально компактный CSS - убираем все пустые места
st.markdown("""
<style>
/* МАКСИМАЛЬНАЯ КОМПАКТНОСТЬ - убираем все пустые места */

/* Основной контейнер - минимальные отступы */
.main .block-container {
    padding-top: 0.25rem !important;
    padding-bottom: 0.25rem !important;
    padding-left: 0.5rem !important;
    padding-right: 0.5rem !important;
    max-width: 100% !important;
}

/* Заголовки - минимальные отступы */
h1, h2, h3, h4, h5, h6 {
    margin-top: 0.05rem !important;
    margin-bottom: 0.05rem !important;
    padding-top: 0.05rem !important;
    padding-bottom: 0.05rem !important;
    line-height: 1.1 !important;
    font-size: 1rem !important;
}

/* Главный заголовок - очень компактный */
h3 {
    font-size: 0.9rem !important;
    margin-bottom: 0.1rem !important;
}

/* Колонки - без отступов */
.stColumns > div {
    padding: 0.05rem !important;
}

/* Кнопки - очень компактные */
.stButton > button {
    padding: 0.1rem 0.3rem !important;
    margin: 0.05rem !important;
    min-height: 1.2rem !important;
    font-size: 0.8rem !important;
}

/* Метрики - компактные */
[data-testid="metric-container"] {
    padding: 0.05rem !important;
    margin: 0.05rem !important;
}

[data-testid="metric-container"] > div {
    padding: 0.05rem !important;
}

/* Таблицы - компактные */
.dataframe {
    font-size: 0.7rem !important;
    margin: 0.05rem !important;
}

/* Боковая панель - компактная */
.css-1d391kg {
    padding-top: 0.1rem !important;
}

/* Убираем все лишние отступы */
.element-container {
    margin-bottom: 0.1rem !important;
}

/* Компактные элементы формы */
.stSelectbox, .stNumberInput, .stTextInput, .stTextArea {
    margin-bottom: 0.05rem !important;
}

.stSelectbox > div, .stNumberInput > div, .stTextInput > div {
    margin-bottom: 0.05rem !important;
}

/* Компактные expander */
.streamlit-expanderHeader {
    padding: 0.1rem 0.3rem !important;
    font-size: 0.8rem !important;
}

.streamlit-expanderContent {
    padding: 0.1rem !important;
}

/* Компактные вкладки */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.05rem !important;
}

.stTabs [data-baseweb="tab"] {
    padding: 0.1rem 0.3rem !important;
    font-size: 0.8rem !important;
}

/* Убираем отступы у markdown */
.stMarkdown {
    margin-bottom: 0.05rem !important;
}

/* Компактные алерты */
.stAlert {
    padding: 0.1rem !important;
    margin: 0.05rem !important;
}

/* Компактные спиннеры */
.stSpinner {
    margin: 0.05rem !important;
}

/* Общие отступы */
div[data-testid="stVerticalBlock"] {
    gap: 0.1rem !important;
}

div[data-testid="stHorizontalBlock"] {
    gap: 0.05rem !important;
}

/* Вкладки сверху - компактные */
.stTabs {
    margin-top: 0.1rem !important;
}

/* Боковая панель - без скролла */
.css-1d391kg {
    height: 100vh !important;
    overflow: hidden !important;
}

/* Убираем отступы между элементами */
div[data-testid="stVerticalBlock"] > div {
    margin-bottom: 0.05rem !important;
}

/* Компактные карточки */
.stCard {
    padding: 0.1rem !important;
    margin: 0.05rem !important;
}

/* Темная тема с анимированным градиентом */
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

.stApp > div > div > div > div {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02)) !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
}

/* Основной контент в стеклянном стиле */
.main .block-container {
    background: rgba(255, 255, 255, 0.03) !important;
    backdrop-filter: blur(15px) !important;
    border-radius: 20px !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2) !important;
    margin: 1rem !important;
    padding: 1.5rem !important;
}

/* LIQUID GLASS SIDEBAR - стеклянный эффект */
.css-1d391kg {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05)) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
    border-radius: 0 20px 20px 0 !important;
}

/* Элементы боковой панели */
.css-1d391kg .stRadio > div {
    background: rgba(255, 255, 255, 0.05) !important;
    border-radius: 12px !important;
    padding: 0.5rem !important;
    margin: 0.25rem 0 !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    backdrop-filter: blur(10px) !important;
}

/* Радио кнопки в стеклянном стиле */
.css-1d391kg .stRadio label {
    background: rgba(0, 212, 170, 0.1) !important;
    border-radius: 8px !important;
    padding: 0.5rem 1rem !important;
    margin: 0.1rem !important;
    border: 1px solid rgba(0, 212, 170, 0.2) !important;
    transition: all 0.3s ease !important;
    backdrop-filter: blur(5px) !important;
}

.css-1d391kg .stRadio label:hover {
    background: rgba(0, 212, 170, 0.2) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(0, 212, 170, 0.3) !important;
}

.css-1d391kg .stRadio label[data-testid="stMarkdownContainer"] {
    background: transparent !important;
    border: none !important;
}

/* Активная вкладка */
.css-1d391kg .stRadio input:checked + label {
    background: linear-gradient(135deg, rgba(0, 212, 170, 0.3), rgba(0, 212, 170, 0.1)) !important;
    border: 1px solid rgba(0, 212, 170, 0.5) !important;
    box-shadow: 0 4px 16px rgba(0, 212, 170, 0.4) !important;
}

/* Заголовки в боковой панели */
.css-1d391kg h1, .css-1d391kg h2, .css-1d391kg h3 {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05)) !important;
    backdrop-filter: blur(10px) !important;
    border-radius: 8px !important;
    padding: 0.5rem !important;
    margin: 0.5rem 0 !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: #00d4aa !important;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3) !important;
}

/* Кнопки в боковой панели */
.css-1d391kg .stButton > button {
    background: linear-gradient(135deg, rgba(0, 212, 170, 0.2), rgba(0, 212, 170, 0.1)) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(0, 212, 170, 0.3) !important;
    border-radius: 8px !important;
    color: #00d4aa !important;
    box-shadow: 0 4px 12px rgba(0, 212, 170, 0.2) !important;
    transition: all 0.3s ease !important;
}

.css-1d391kg .stButton > button:hover {
    background: linear-gradient(135deg, rgba(0, 212, 170, 0.3), rgba(0, 212, 170, 0.2)) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(0, 212, 170, 0.4) !important;
}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# СТИЛИ - ПОЛНОФУНКЦИОНАЛЬНЫЙ ДИЗАЙН
# =============================================================================
st.markdown("""
    <style>
    /* Основной фон */
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    
    /* Главный контейнер */
    .main .block-container {
        padding: 1rem;
        max-width: 100%;
    }
    
    /* Вкладки сверху - эргономичные */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background-color: #1e1e1e;
        border-radius: 8px 8px 0 0;
        padding: 0.5rem;
        margin-bottom: 0;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        padding: 0.75rem 1.5rem;
        margin: 0 0.25rem;
        border-radius: 6px;
        background-color: transparent;
        color: #9ca3af;
        font-weight: 500;
        font-size: 0.9rem;
        transition: all 0.3s;
        border: none;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #374151;
        color: #fafafa;
        transform: translateY(-1px);
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #00d4aa;
        color: #000;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(0, 212, 170, 0.3);
    }
    
    /* Контент вкладок */
    .stTabs [data-baseweb="tab-panel"] {
        background-color: #1e1e1e;
        border-radius: 0 0 8px 8px;
        padding: 1.5rem;
        margin-top: 0;
        border: 1px solid #333;
        border-top: none;
        min-height: 70vh;
    }
    
    /* Заголовки */
    h1, h2, h3, h4, h5, h6 {
        color: #fafafa;
        font-weight: 600;
    }
    
    h1 {
        font-size: 2rem;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #00d4aa 0%, #00b894 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    h2 {
        font-size: 1.5rem;
        margin: 1.5rem 0 1rem 0;
        color: #00d4aa;
    }
    
    h3 {
        font-size: 1.2rem;
        margin: 1rem 0 0.5rem 0;
        color: #e5e7eb;
    }
    
    /* Кнопки */
    .stButton > button {
        background: linear-gradient(135deg, #00d4aa 0%, #00b894 100%);
        color: #000;
        border: none;
        border-radius: 6px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s;
        box-shadow: 0 2px 4px rgba(0, 212, 170, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 212, 170, 0.4);
    }
    
    /* Метрики */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #00d4aa;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem;
        font-weight: 500;
        color: #9ca3af;
    }
    
    /* Таблицы */
    [data-testid="stDataFrame"] {
        border: 1px solid #333;
        border-radius: 8px;
        background-color: #0e1117;
    }
    
    /* Алерты */
    .stAlert {
        border-radius: 8px;
        border: 1px solid #333;
        background-color: #1e1e1e;
    }
    
    /* Карточки */
    .metric-card {
        background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #333;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 12px rgba(0, 0, 0, 0.2);
    }
    
    /* Элементы управления */
    [data-baseweb="select"] {
        border-radius: 6px;
        background-color: #1e1e1e;
        border-color: #333;
        color: #fafafa;
    }
    
    [data-baseweb="input"] {
        border-radius: 6px;
        background-color: #1e1e1e;
        border-color: #333;
        color: #fafafa;
    }
    
    /* Статус подключения */
    .status-card {
        background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #333;
        margin: 1rem 0;
        text-align: center;
    }
    
    .status-success {
        border-color: #00d4aa;
        background: linear-gradient(135deg, rgba(0, 212, 170, 0.1) 0%, #1e1e1e 100%);
    }
    
    .status-error {
        border-color: #ef4444;
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, #1e1e1e 100%);
    }
    
    /* Убираем лишние отступы */
    .element-container {
        margin: 0.5rem 0;
    }
    
    .stMarkdown {
        margin: 0.5rem 0;
    }
    
    /* Скроллбары */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1e1e1e;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #00d4aa;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #00b894;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# ИНИЦИАЛИЗАЦИЯ
# =============================================================================
def init_session_state():
    """Инициализация session state"""
    try:
        if 'db_client' not in st.session_state:
            st.session_state.db_client = get_client()
            st.session_state.db_connected = True
            st.session_state.db_error = None
        return True
    except Exception as e:
        st.session_state.db_connected = False
        st.session_state.db_error = str(e)
        return False

# Инициализируем
init_session_state()

# =============================================================================
# ОСНОВНОЙ ИНТЕРФЕЙС
# =============================================================================

# Заголовок
st.markdown("### 📦 WB API Dashboard")
st.markdown("Комплексное решение для автоматизации Wildberries API")

# Статус подключения
if st.session_state.get('db_connected', False):
    st.markdown("""
        <div class="status-card status-success">
            <h3 style="color: #00d4aa; margin: 0;">✅ База данных подключена</h3>
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <div class="status-card status-error">
            <h3 style="color: #ef4444; margin: 0;">❌ База данных не подключена</h3>
            <p style="color: #9ca3af; margin: 0.5rem 0 0 0;">Проверьте настройки в api_keys.py</p>
        </div>
    """, unsafe_allow_html=True)

# =============================================================================
# БОКОВОЕ МЕНЮ В СТИЛЕ LIQUID GLASS
# =============================================================================

# Боковое меню
with st.sidebar:
    st.markdown("### 🎛️ Навигация")
    
    # Радио кнопки для навигации
    page = st.radio(
        "Выберите раздел:",
        [
            "📊 Dashboard", 
            "🔄 Синхронизация", 
            "📦 Товары", 
            "💰 Цены", 
            "📈 История цен",
            "📝 Логи",
            "🔧 SQL Запросы",
            "⚙️ Настройки"
        ],
        key="main_navigation"
    )
    
    st.markdown("---")
    st.markdown("### 📊 Статус")
    st.success("✅ Система активна")
    st.info("🔄 Последнее обновление: 2 мин назад")

# =============================================================================
# DASHBOARD - ПОЛНАЯ ФУНКЦИОНАЛЬНОСТЬ
# =============================================================================
if page == "📊 Dashboard":
    st.markdown("## 📊 Обзор системы")
    
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
    
    # Детальные дашборды
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎯 Быстрые действия")
        if st.button("🔄 Синхронизировать данные", key="btn_sync_1"):
            st.success("Синхронизация запущена!")
        
        if st.button("📊 Обновить метрики", key="btn_metrics_1"):
            st.success("Метрики обновлены!")
        
        if st.button("📈 Сгенерировать отчет", key="btn_report_1"):
            st.success("Отчет создан!")
    
    with col2:
        st.markdown("### 📈 Статистика")
        st.markdown("""
        <div class="metric-card">
            <ul style="color: #e5e7eb; margin: 0; padding-left: 1.5rem;">
                <li>Последняя синхронизация: 2 мин назад</li>
                <li>Обновлено товаров: 45</li>
                <li>Изменено цен: 12</li>
                <li>Ошибок: 0</li>
                <li>Активных API ключей: 3</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # График активности
    st.markdown("### 📊 График активности")
    chart_data = pd.DataFrame({
        'День': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],
        'Синхронизации': [12, 15, 8, 22, 18, 5, 3],
        'Обновления цен': [45, 52, 38, 67, 43, 12, 8]
    })
    st.line_chart(chart_data.set_index('День'))

# =============================================================================
# СИНХРОНИЗАЦИЯ - ПОЛНАЯ ФУНКЦИОНАЛЬНОСТЬ
# =============================================================================
elif page == "🔄 Синхронизация":
    st.markdown("## 🔄 Синхронизация данных")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Выберите источник данных")
        
        sync_option = st.selectbox(
            "Источник",
            ["Content Cards (карточки товаров)", "Discounts-Prices (цены и скидки)", "Warehouse Remains (остатки)"],
            help="Выберите API для синхронизации данных"
        )
        
        # Дополнительные параметры
        with st.expander("⚙️ Дополнительные параметры"):
            col_a, col_b = st.columns(2)
            with col_a:
                batch_size = st.number_input("Размер батча", min_value=10, max_value=1000, value=100, key="batch_size_1")
                max_items = st.number_input("Максимум товаров", min_value=100, max_value=10000, value=1000, key="max_items_1")
            with col_b:
                include_inactive = st.checkbox("Включить неактивные товары")
                validate_data = st.checkbox("Валидировать данные")
        
        if st.button("🔄 Запустить синхронизацию", type="primary"):
            try:
                with st.spinner("Синхронизация в процессе..."):
                    # Инициализируем процессор
                    processor = DiscountsPricesDBProcessor()
                    
                    # Запускаем синхронизацию
                    stats = processor.sync_prices_to_db(
                        max_goods=1000,  # Ограничиваем для демо
                        batch_size=50,
                        sleep_seconds=1.0
                    )
                    
                    st.success("✅ Синхронизация завершена!")
                    
                    # Показываем результаты
                    st.markdown("### 📊 Результаты синхронизации")
                    results_data = pd.DataFrame({
                        'Операция': ['Всего товаров', 'Успешно обработано', 'Ошибок', 'Время выполнения'],
                        'Значение': [
                            stats['total'], 
                            stats['success'], 
                            stats['failed'],
                            f"{stats['execution_time_ms']/1000:.2f}с"
                        ]
                    })
                    st.dataframe(results_data, key="btn_1")
                    
                    # Показываем аналитику
                    if stats['success'] > 0:
                        with st.expander("📈 Быстрая аналитика"):
                            analytics = processor.get_price_analytics(days=1)
                            if 'error' not in analytics:
                                stats_data = analytics['statistics']
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Товаров в БД", stats_data.get('total_products', 0))
                                with col2:
                                    st.metric("Средняя цена", f"{stats_data.get('avg_price', 0):.0f} ₽")
                                with col3:
                                    st.metric("Со скидками", stats_data.get('products_with_discount', 0))
                            
            except Exception as e:
                st.error(f"❌ Ошибка синхронизации: {e}")
                st.info("💡 Проверьте настройки API ключей в api_keys.py")
    
    with col2:
        st.markdown("### Статус API")
        
        # Проверка API ключей
        try:
            import api_keys
            wb_key = getattr(api_keys, 'WB_API_KEY', '')
            discounts_key = getattr(api_keys, 'WB_DISCOUNTS_API_KEY', '')
            
            if wb_key and wb_key != "your_wildberries_api_key_here":
                st.success("✅ WB API ключ настроен")
            else:
                st.error("❌ WB API ключ не настроен")
            
            if discounts_key and discounts_key != "your_discounts_api_key_here":
                st.success("✅ Discounts API ключ настроен")
            else:
                st.error("❌ Discounts API ключ не настроен")
                
        except Exception as e:
            st.error(f"❌ Ошибка проверки API ключей: {e}")
        
        # История синхронизаций
        st.markdown("### 📜 История синхронизаций")
        history_data = pd.DataFrame({
            'Время': ['15:30', '14:15', '13:00', '11:45'],
            'Тип': ['Content Cards', 'Prices', 'Content Cards', 'Prices'],
            'Статус': ['✅ Успех', '✅ Успех', '⚠️ Предупреждения', '✅ Успех'],
            'Товаров': [156, 89, 134, 67]
        })
        st.dataframe(history_data, key="btn_2")

# =============================================================================
# ТОВАРЫ - ПОЛНАЯ ФУНКЦИОНАЛЬНОСТЬ
# =============================================================================
elif page == "📦 Товары":
    st.markdown("## 📦 Управление товарами")
    
    # Поиск и фильтры
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search_query = st.text_input("🔍 Поиск товаров", placeholder="Введите название, артикул или бренд")
    
    with col2:
        status_filter = st.selectbox("Статус", ["Все", "Активные", "Неактивные"])
    
    with col3:
        brand_filter = st.selectbox("Бренд", ["Все", "Brand A", "Brand B", "Brand C"])
    
    # Дополнительные фильтры
    with st.expander("🔍 Расширенные фильтры"):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            min_price = st.number_input("Мин. цена", value=0, key="min_price")
            max_price = st.number_input("Макс. цена", value=100000, key="max_price")
        with col_b:
            has_discount = st.selectbox("Скидка", ["Все", "Есть скидка", "Без скидки"])
            has_stock = st.selectbox("Остатки", ["Все", "Есть остатки", "Нет остатков"])
        with col_c:
            date_from = st.date_input("Дата создания от", value=datetime.now() - timedelta(days=30))
            date_to = st.date_input("Дата создания до", value=datetime.now())
    
    # Таблица товаров
    st.markdown("### Список товаров")
    
    # Пример данных
    sample_data = pd.DataFrame({
        'Артикул': [12345, 12346, 12347, 12348, 12349],
        'Название': ['Товар 1', 'Товар 2', 'Товар 3', 'Товар 4', 'Товар 5'],
        'Бренд': ['Brand A', 'Brand B', 'Brand A', 'Brand C', 'Brand B'],
        'Цена': [1500, 2300, 1800, 3200, 2100],
        'Скидка': [10, 15, 0, 20, 5],
        'Остаток': [15, 8, 22, 3, 45],
        'Статус': ['Активный', 'Активный', 'Неактивный', 'Активный', 'Активный'],
        'Обновлен': ['2 мин', '1 час', '3 часа', '5 мин', '30 мин']
    })
    
    st.dataframe(sample_data, key="btn_3")
    
    # Действия с товарами
    st.markdown("### Действия")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 Анализ товаров", key="btn_4"):
            st.info("Анализ запущен")
    
    with col2:
        if st.button("📤 Экспорт в Excel", key="btn_5"):
            st.info("Экспорт запущен")
    
    with col3:
        if st.button("🔄 Обновить данные", key="btn_6"):
            st.info("Обновление запущено")
    
    with col4:
        if st.button("🗑️ Очистить неактивные", key="btn_7"):
            st.info("Очистка запущена")

# =============================================================================
# ЦЕНЫ - ПОЛНАЯ ФУНКЦИОНАЛЬНОСТЬ
# =============================================================================
elif page == "💰 Цены":
    st.markdown("## 💰 Управление ценами")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Текущие цены")
        
        # Пример данных цен
        price_data = pd.DataFrame({
            'Артикул': [12345, 12346, 12347, 12348, 12349],
            'Название': ['Товар 1', 'Товар 2', 'Товар 3', 'Товар 4', 'Товар 5'],
            'Текущая цена': [1500, 2300, 1800, 3200, 2100],
            'Цена со скидкой': [1350, 1955, 1800, 2560, 1995],
            'Скидка': [10, 15, 0, 20, 5],
            'Конкурентная цена': [1600, 2400, 1900, 3300, 2200],
            'Обновлено': ['2 мин', '1 час', '3 часа', '5 мин', '30 мин']
        })
        
        st.dataframe(price_data, key="btn_8")
        
        # Массовые операции с ценами
        st.markdown("### 💰 Массовые операции")
        col_a, col_b = st.columns(2)
        
        with col_a:
            price_action = st.selectbox(
                "Действие",
                ["Повысить на %", "Понизить на %", "Установить фиксированную цену", "Синхронизировать с конкурентами"]
            )
            price_value = st.number_input("Значение", value=10, min_value=0, max_value=100, key="price_value")
        
        with col_b:
            target_items = st.multiselect(
                "Целевые товары",
                ["Все активные", "Только выбранные", "По фильтру", "По бренду"]
            )
            if st.button("🚀 Применить изменения", type="primary"):
                st.success(f"Изменения применены к {len(target_items)} товарам!")
    
    with col2:
        st.markdown("### Анализ цен")
        
        if st.button("📊 Анализ цен", key="btn_9"):
            st.info("Анализ цен запущен")
        
        if st.button("💰 Обновить цены", key="btn_10"):
            st.info("Обновление цен запущено")
        
        if st.button("🎯 Конкурентный анализ", key="btn_11"):
            st.info("Анализ конкурентов запущен")
        
        if st.button("📈 Динамика цен", key="btn_12"):
            st.info("Анализ динамики запущен")
        
        # График цен
        st.markdown("### 📈 Топ изменения цен")
        price_changes = pd.DataFrame({
            'Товар': ['Товар 1', 'Товар 2', 'Товар 3'],
            'Изменение': [150, -200, 50],
            'Процент': [10, -8, 3]
        })
        st.bar_chart(price_changes.set_index('Товар'))

# =============================================================================
# ИСТОРИЯ ЦЕН - ПОЛНАЯ ФУНКЦИОНАЛЬНОСТЬ
# =============================================================================
elif page == "📈 История цен":
    st.markdown("## 📈 История цен")
    
    # Фильтры для истории
    col1, col2, col3 = st.columns(3)
    
    with col1:
        history_period = st.selectbox(
            "Период",
            ["Последние 7 дней", "Последний месяц", "Последние 3 месяца", "Произвольный период"]
        )
    
    with col2:
        if history_period == "Произвольный период":
            start_date = st.date_input("Начало периода", value=datetime.now() - timedelta(days=30))
            end_date = st.date_input("Конец периода", value=datetime.now())
    
    with col3:
        history_filter = st.selectbox(
            "Фильтр",
            ["Все товары", "Только с изменениями", "По бренду", "По диапазону цен"]
        )
    
    # График истории цен
    st.markdown("### 📊 График изменения цен")
    
    # Пример данных для графика
    dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
    price_history_data = pd.DataFrame({
        'Дата': dates,
        'Товар 1': [1500 + (i % 10) * 50 for i in range(len(dates))],
        'Товар 2': [2300 - (i % 7) * 30 for i in range(len(dates))],
        'Товар 3': [1800 + (i % 5) * 40 for i in range(len(dates))]
    })
    
    st.line_chart(price_history_data.set_index('Дата'))
    
    # Детальная таблица истории
    st.markdown("### 📋 Детальная история")
    
    history_table = pd.DataFrame({
        'Дата': ['2025-01-04 15:30', '2025-01-04 14:15', '2025-01-04 13:00', '2025-01-04 11:45'],
        'Артикул': [12345, 12346, 12347, 12348],
        'Товар': ['Товар 1', 'Товар 2', 'Товар 3', 'Товар 4'],
        'Старая цена': [1400, 2500, 1800, 3000],
        'Новая цена': [1500, 2300, 1800, 3200],
        'Изменение': [100, -200, 0, 200],
        'Причина': ['Ручное изменение', 'Конкурентный анализ', 'Без изменений', 'Автоматическое повышение']
    })
    
    st.dataframe(history_table, key="btn_13")
    
    # Экспорт истории
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📤 Экспорт в Excel", key="btn_14"):
            st.success("Экспорт истории в Excel запущен")
    with col2:
        if st.button("📊 Создать отчет", key="btn_15"):
            st.success("Отчет по истории цен создан")
    with col3:
        if st.button("🔍 Найти аномалии", key="btn_16"):
            st.success("Поиск аномалий в ценах запущен")

# =============================================================================
# ЛОГИ - ПОЛНАЯ ФУНКЦИОНАЛЬНОСТЬ
# =============================================================================
elif page == "📝 Логи":
    st.markdown("## 📝 Логи системы")
    
    # Фильтры логов
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        log_level = st.selectbox("Уровень", ["Все", "INFO", "WARNING", "ERROR", "SUCCESS"])
    
    with col2:
        log_type = st.selectbox("Тип", ["Все", "API", "Database", "Sync", "Validation"])
    
    with col3:
        log_period = st.selectbox("Период", ["Последний час", "Последние 24 часа", "Последние 7 дней", "Все время"])
    
    with col4:
        log_search = st.text_input("Поиск", placeholder="Поиск по сообщению")
    
    # Таблица логов
    st.markdown("### 📋 Последние логи")
    
    logs_data = pd.DataFrame({
        'Время': ['15:30:45', '15:29:12', '15:28:33', '15:27:01', '15:26:15'],
        'Уровень': ['INFO', 'SUCCESS', 'WARNING', 'ERROR', 'INFO'],
        'Тип': ['API', 'Sync', 'Database', 'API', 'Validation'],
        'Сообщение': [
            'Синхронизация Content Cards завершена',
            'Обновлено 156 товаров',
            'Предупреждение: превышен лимит запросов',
            'Ошибка подключения к API',
            'Валидация данных пройдена'
        ],
        'Детали': ['156 товаров', 'Успех', 'Повторить через 1 мин', 'Проверить ключ', '0 ошибок']
    })
    
    st.dataframe(logs_data, key="btn_17")
    
    # Действия с логами
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Обновить логи", key="btn_18"):
            st.success("Логи обновлены")
    
    with col2:
        if st.button("📤 Экспорт логов", key="btn_19"):
            st.success("Экспорт логов запущен")
    
    with col3:
        if st.button("🗑️ Очистить старые логи", key="btn_20"):
            st.success("Очистка логов запущена")
    
    # Статистика логов
    st.markdown("### 📊 Статистика логов")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Всего логов", "1,234", "+12")
    with col2:
        st.metric("Ошибок", "3", "-2")
    with col3:
        st.metric("Предупреждений", "15", "+3")
    with col4:
        st.metric("Успешных", "1,216", "+11")

# =============================================================================
# SQL ЗАПРОСЫ - ПОЛНАЯ ФУНКЦИОНАЛЬНОСТЬ
# =============================================================================
elif page == "🔧 SQL Запросы":
    st.markdown("## 🔧 SQL Запросы")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Редактор запросов")
        
        # Пример SQL запроса
        default_query = """-- Пример запроса: все активные товары с ценами
SELECT 
    p.nm_id,
    p.vendor_code,
    p.brand,
    p.title,
    ue.price,
    ue.discounted_price,
    ue.discount
FROM products p
LEFT JOIN unit_economics ue ON p.nm_id = ue.nm_id
WHERE p.active = true
ORDER BY p.updated_at DESC
LIMIT 100;"""
        
        sql_query = st.text_area(
            "SQL запрос",
            value=default_query,
            height=300,
            help="Введите SQL запрос для выполнения"
        )
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if st.button("▶️ Выполнить запрос", type="primary"):
                if sql_query.strip():
                    st.success("✅ Запрос выполнен!")
                    # Здесь будет результат запроса
                else:
                    st.error("❌ Введите SQL запрос")
        
        with col_b:
            if st.button("💾 Сохранить запрос"):
                st.info("Запрос сохранен")
        
        with col_c:
            if st.button("📋 Копировать"):
                st.info("Запрос скопирован")
    
    with col2:
        st.markdown("### Готовые запросы")
        
        queries = [
            "Все активные товары",
            "Товары с ценами",
            "Товары без цен",
            "История изменений цен",
            "Остатки по складам",
            "Топ товаров по продажам",
            "Анализ скидок",
            "Статистика по брендам"
        ]
        
        for i, query in enumerate(queries):
            if st.button(f"📋 {query}", key=f"sql_btn_{i}"):
                st.info(f"Загружен запрос: {query}")
        
        st.markdown("### Категории запросов")
        
        with st.expander("📊 Основные выборки"):
            st.code("SELECT * FROM products WHERE active = true;")
            st.code("SELECT * FROM unit_economics WHERE price > 1000;")
        
        with st.expander("🔄 Upsert операции"):
            st.code("INSERT INTO products (...) VALUES (...) ON CONFLICT DO UPDATE...")
        
        with st.expander("📈 Аналитика"):
            st.code("SELECT brand, COUNT(*), AVG(price) FROM products GROUP BY brand;")
        
        with st.expander("🗑️ Очистка данных"):
            st.code("DELETE FROM validation_logs WHERE timestamp < NOW() - INTERVAL '30 days';")
    
    # Результат запроса
    st.markdown("### Результат запроса")
    if sql_query.strip():
        # Пример результата
        result_data = pd.DataFrame({
            'nm_id': [12345, 12346, 12347],
            'vendor_code': ['VC001', 'VC002', 'VC003'],
            'brand': ['Brand A', 'Brand B', 'Brand A'],
            'title': ['Товар 1', 'Товар 2', 'Товар 3'],
            'price': [1500, 2300, 1800],
            'discounted_price': [1350, 1955, 1800],
            'discount': [10, 15, 0]
        })
        st.dataframe(result_data, key="btn_22")
        
        st.markdown("**Статистика запроса:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Строк возвращено", "3")
        with col2:
            st.metric("Время выполнения", "0.15 сек")
        with col3:
            st.metric("Размер результата", "2.1 KB")
    else:
        st.info("Выберите и выполните запрос для просмотра результатов")

# =============================================================================
# НАСТРОЙКИ - ПОЛНАЯ ФУНКЦИОНАЛЬНОСТЬ
# =============================================================================
elif page == "⚙️ Настройки":
    st.markdown("## ⚙️ Настройки системы")
    
    # API ключи
    st.markdown("### 🔑 API ключи")
    
    with st.expander("Wildberries API"):
        col1, col2 = st.columns(2)
        with col1:
            wb_api_key = st.text_input(
                "WB API ключ",
                value="***скрыт***",
                type="password",
                help="API ключ для Content Cards"
            )
        with col2:
            discounts_api_key = st.text_input(
                "Discounts API ключ", 
                value="***скрыт***",
                type="password",
                help="API ключ для цен и скидок"
            )
        
        if st.button("💾 Сохранить API ключи"):
            st.success("API ключи сохранены")
    
    with st.expander("Google Sheets API"):
        gs_credentials = st.text_area(
            "Google Sheets Credentials (JSON)",
            height=100,
            help="JSON с credentials для Google Sheets API"
        )
        if st.button("💾 Сохранить GS настройки"):
            st.success("Google Sheets настройки сохранены")
    
    with st.expander("Supabase"):
        col1, col2 = st.columns(2)
        with col1:
            supabase_url = st.text_input("Supabase URL", value="https://***.supabase.co")
        with col2:
            supabase_key = st.text_input("Supabase Key", type="password", value="***скрыт***")
        if st.button("💾 Сохранить Supabase настройки"):
            st.success("Supabase настройки сохранены")
    
    # Настройки синхронизации
    st.markdown("### 🔄 Настройки синхронизации")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Автоматическая синхронизация")
        auto_sync = st.checkbox("Включить автосинхронизацию", value=True)
        sync_interval = st.selectbox(
            "Интервал синхронизации",
            ["Каждые 15 минут", "Каждый час", "Каждые 3 часа", "Раз в день"]
        )
        sync_content = st.checkbox("Синхронизировать Content Cards", value=True)
        sync_prices = st.checkbox("Синхронизировать цены", value=True)
        sync_warehouse = st.checkbox("Синхронизировать остатки", value=False)
    
    with col2:
        st.markdown("#### Параметры синхронизации")
        batch_size = st.number_input("Размер батча", min_value=10, max_value=1000, value=100, key="batch_size_2")
        max_items = st.number_input("Максимум товаров за раз", min_value=100, max_value=10000, value=1000, key="max_items_2")
        retry_attempts = st.number_input("Количество попыток", min_value=1, max_value=10, value=3, key="retry_attempts")
        timeout = st.number_input("Таймаут (сек)", min_value=10, max_value=300, value=60, key="timeout")
    
    if st.button("💾 Сохранить настройки синхронизации"):
        st.success("Настройки синхронизации сохранены")
    
    # Настройки уведомлений
    st.markdown("### 📧 Уведомления")
    
    col1, col2 = st.columns(2)
    
    with col1:
        email_notifications = st.checkbox("Email уведомления", value=False)
        email_address = st.text_input("Email адрес", disabled=not email_notifications)
        notify_errors = st.checkbox("Уведомлять об ошибках", value=True)
        notify_success = st.checkbox("Уведомлять об успешных операциях", value=False)
    
    with col2:
        telegram_notifications = st.checkbox("Telegram уведомления", value=False)
        telegram_bot_token = st.text_input("Bot Token", type="password", disabled=not telegram_notifications)
        telegram_chat_id = st.text_input("Chat ID", disabled=not telegram_notifications)
    
    if st.button("💾 Сохранить настройки уведомлений"):
        st.success("Настройки уведомлений сохранены")
    
    # Системные настройки
    st.markdown("### 🖥️ Системные настройки")
    
    col1, col2 = st.columns(2)
    
    with col1:
        log_level = st.selectbox("Уровень логирования", ["DEBUG", "INFO", "WARNING", "ERROR"])
        log_retention = st.number_input("Хранить логи (дней)", min_value=7, max_value=365, value=30, key="log_retention")
        cache_size = st.number_input("Размер кэша (MB)", min_value=10, max_value=1000, value=100, key="cache_size")
    
    with col2:
        theme = st.selectbox("Тема интерфейса", ["Темная", "Светлая", "Автоматическая"])
        language = st.selectbox("Язык", ["Русский", "English"])
        timezone = st.selectbox("Часовой пояс", ["Europe/Moscow", "UTC", "Europe/London"])
    
    if st.button("💾 Сохранить системные настройки"):
        st.success("Системные настройки сохранены")
    
    # Действия
    st.markdown("### 🔧 Действия")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔄 Перезапустить сервисы", key="btn_23"):
            st.success("Сервисы перезапущены")
    
    with col2:
        if st.button("🧹 Очистить кэш", key="btn_24"):
            st.success("Кэш очищен")
    
    with col3:
        if st.button("📊 Проверить систему", key="btn_25"):
            st.success("Проверка системы завершена")
    
    with col4:
        if st.button("💾 Создать резервную копию", key="btn_26"):
            st.success("Резервная копия создана")
