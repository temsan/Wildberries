"""
Веб-интерфейс для управления БД Wildberries (Streamlit).
Автозапуск: python database/web_interface.py
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
from pathlib import Path

# Добавляем корневую директорию в path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.db_client import get_client
from database.integrations.content_cards_db import sync_content_cards_to_db
from database.integrations.discounts_prices_db import sync_discounts_prices_to_db

# Настройка страницы
st.set_page_config(
    page_title="WB API Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Кастомные стили - чистый минималистичный дизайн
st.markdown("""
    <style>
    /* Основной фон */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Боковая панель */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }
    
    /* Убираем радиокнопки из навигации */
    [data-testid="stSidebar"] [role="radiogroup"] {
        display: none;
    }
    
    /* Метрики */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 600;
    }
    
    /* Кнопки */
    .stButton > button {
        border-radius: 6px;
        border: 1px solid #e0e0e0;
        background-color: white;
        color: #333;
        font-weight: 500;
    }
    
    .stButton > button:hover {
        border-color: #4285f4;
        color: #4285f4;
    }
    
    /* Таблицы */
    [data-testid="stDataFrame"] {
        border: 1px solid #e0e0e0;
    }
    
    /* Заголовки */
    h1 {
        color: #333;
        font-weight: 600;
    }
    
    h2, h3 {
        color: #555;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# Инициализация session state (только если Streamlit контекст активен)
def init_session_state():
    try:
        if 'db_client' not in st.session_state:
            st.session_state.db_client = get_client()
            st.session_state.db_connected = True
        return True
    except Exception as e:
        if 'db_connected' not in st.session_state:
            st.session_state.db_connected = False
            st.session_state.db_error = str(e)
        return False

# Инициализация page в session_state
if 'page' not in st.session_state:
    st.session_state.page = "📊 Dashboard"

# Боковая панель
with st.sidebar:
    st.title("📦 WB API")
    st.caption("Dashboard & Analytics")
    
    st.divider()

    # Инициализируем session state для боковой панели
    init_session_state()

    # Статус подключения
    if st.session_state.get('db_connected', False):
        st.success("✅ БД подключена")
    else:
        st.error("❌ БД не подключена")
        with st.expander("Подробнее"):
            st.warning(st.session_state.get('db_error', 'Неизвестная ошибка'))
            st.info("Проверьте SUPABASE_URL и SUPABASE_KEY в api_keys.py")
    
    st.divider()
    
    # Навигация с кнопками
    st.subheader("Навигация")
    
    pages = [
        ("📊", "Dashboard"),
        ("🔄", "Синхронизация"),
        ("📦", "Товары"),
        ("💰", "Цены"),
        ("📈", "История цен"),
        ("📝", "Логи"),
        ("🔧", "SQL Запросы"),
        ("⚙️", "Настройки")
    ]
    
    for icon, name in pages:
        page_key = f"{icon} {name}"
        if st.button(
            f"{icon} {name}",
            key=f"nav_{name}",
            use_container_width=True,
            type="primary" if st.session_state.page == page_key else "secondary"
        ):
            st.session_state.page = page_key
            st.rerun()
    
    st.divider()
    
    # Информация
    st.caption("**Версия:** 1.0.0")
    st.caption("**Год:** 2025")
    st.caption("[📚 Документация](database/WEB_INTERFACE.md)")

# Получаем текущую страницу
page = st.session_state.page

# =============================================================================
# DASHBOARD
# =============================================================================
if page == "📊 Dashboard":
    st.title("📊 WB API Dashboard")
    
    # Инициализируем session state
    if not init_session_state():
        st.error("❌ БД не подключена. Проверьте настройки.")
        st.stop()

    if not st.session_state.db_connected:
        st.error("❌ БД не подключена. Проверьте настройки.")
        st.stop()

    db = st.session_state.db_client
    
    # Выбор шаблона дашборда
    st.sidebar.markdown("---")
    dashboard_template = st.sidebar.selectbox(
        "📊 Шаблон дашборда",
        [
            "📈 Общий обзор",
            "📦 Товарооборот",
            "💰 Юнит-экономика",
            "💼 Финансы (ОПиУ)",
            "🚚 Логистика"
        ]
    )
    
    # Кнопка обновления
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🔄 Обновить"):
            st.rerun()
    
    try:
        products = db.get_active_products()
        barcodes = db.get_active_barcodes()
        products_with_prices = db.get_products_with_prices()
        
        # =============================================================================
        # ШАБЛОН: ОБЩИЙ ОБЗОР
        # =============================================================================
        if dashboard_template == "📈 Общий обзор":
            st.markdown("### 📈 Основные метрики")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "📦 Активных товаров",
                    len(products),
                    help="Количество активных товаров в базе"
                )
            with col2:
                st.metric(
                    "🏷️ Активных баркодов",
                    len(barcodes),
                    help="Количество уникальных баркодов (SKU)"
                )
            with col3:
                st.metric(
                    "💰 Товаров с ценами",
                    len(products_with_prices),
                    help="Товары с установленными ценами"
                )
            with col4:
                coverage = (len(products_with_prices) / len(products) * 100) if products else 0
                st.metric(
                    "📊 Покрытие ценами",
                    f"{coverage:.1f}%",
                    help="Процент товаров с установленными ценами"
                )
            
            st.divider()
            
            # Финансовые метрики
            st.markdown("### 💵 Финансовые показатели")
            
            if products_with_prices:
                total_price = sum(p.get('price', 0) or 0 for p in products_with_prices)
                avg_price = total_price / len(products_with_prices) if products_with_prices else 0
                avg_discount = sum(p.get('discount', 0) or 0 for p in products_with_prices) / len(products_with_prices) if products_with_prices else 0
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("💰 Средняя цена", f"{avg_price:,.2f} ₽")
                with col2:
                    st.metric("🏷️ Средняя скидка", f"{avg_discount:.1f}%")
                with col3:
                    max_price = max((p.get('price', 0) or 0 for p in products_with_prices), default=0)
                    st.metric("📈 Макс. цена", f"{max_price:,.2f} ₽")
                with col4:
                    min_price = min((p.get('price', 0) or 0 for p in products_with_prices if p.get('price', 0)), default=0)
                    st.metric("📉 Мин. цена", f"{min_price:,.2f} ₽")
            else:
                st.info("📊 Нет данных о ценах. Выполните синхронизацию цен.")
            
            st.divider()
            
            # Последние операции
            st.markdown("### 📝 Последние операции")
            
            logs = db.get_recent_logs(limit=10)
            if logs:
                logs_df = pd.DataFrame(logs)
                logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                
                def format_status(status):
                    if status == 'success':
                        return '✅ Успешно'
                    elif status == 'warning':
                        return '⚠️ Предупреждение'
                    else:
                        return '❌ Ошибка'
                
                logs_df['status_formatted'] = logs_df['status'].apply(format_status)
                
                st.dataframe(
                    logs_df[['timestamp', 'operation_type', 'status_formatted', 'records_processed', 'records_failed']].rename(columns={
                        'timestamp': 'Время',
                        'operation_type': 'Операция',
                        'status_formatted': 'Статус',
                        'records_processed': 'Обработано',
                        'records_failed': 'Ошибок'
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("📋 Нет записей в логах")
            
            st.divider()
            
            # Топ товаров
            st.markdown("### 💎 Топ товаров")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**💰 Самые дорогие**")
                if products_with_prices:
                    top_expensive = sorted(products_with_prices, key=lambda x: x.get('price', 0) or 0, reverse=True)[:5]
                    for idx, item in enumerate(top_expensive, 1):
                        brand = item.get('brand', 'N/A')
                        price = item.get('price', 0)
                        vendor_code = item.get('vendor_code', 'N/A')
                        st.write(f"{idx}. **{brand}** ({vendor_code}) - {price:,.2f} ₽")
                else:
                    st.info("Нет данных")
            
            with col2:
                st.markdown("**🏷️ Максимальные скидки**")
                if products_with_prices:
                    top_discounts = sorted(products_with_prices, key=lambda x: x.get('discount', 0) or 0, reverse=True)[:5]
                    for idx, item in enumerate(top_discounts, 1):
                        brand = item.get('brand', 'N/A')
                        discount = item.get('discount', 0)
                        vendor_code = item.get('vendor_code', 'N/A')
                        st.write(f"{idx}. **{brand}** ({vendor_code}) - {discount}%")
                else:
                    st.info("Нет данных")
        
        # =============================================================================
        # ШАБЛОН: ТОВАРООБОРОТ
        # =============================================================================
        elif dashboard_template == "📦 Товарооборот":
            st.markdown("### 📦 Товарооборот и управление запасами")
            
            # Метрики товарооборота
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "📦 Всего товаров",
                    len(products),
                    help="Количество активных товаров"
                )
            with col2:
                st.metric(
                    "🏷️ Всего SKU",
                    len(barcodes),
                    help="Количество уникальных баркодов"
                )
            with col3:
                # Подсчет товаров с ценами как показатель готовности к продаже
                ready_to_sell = len(products_with_prices)
                st.metric(
                    "✅ Готовы к продаже",
                    ready_to_sell,
                    help="Товары с установленными ценами"
                )
            with col4:
                coverage = (ready_to_sell / len(products) * 100) if products else 0
                st.metric(
                    "📊 Готовность",
                    f"{coverage:.0f}%",
                    help="Процент товаров готовых к продаже"
                )
            
            st.divider()
            
            # Анализ по брендам
            st.markdown("### 🏷️ Распределение по брендам")
            
            if products:
                # Подсчет товаров по брендам
                brand_counts = {}
                for p in products:
                    brand = p.get('brand', 'Без бренда')
                    brand_counts[brand] = brand_counts.get(brand, 0) + 1
                
                # Топ-5 брендов
                top_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # График
                    brand_data = {brand: count for brand, count in top_brands}
                    st.bar_chart(brand_data)
                
                with col2:
                    st.markdown("**Топ-5 брендов:**")
                    for idx, (brand, count) in enumerate(top_brands, 1):
                        percentage = (count / len(products) * 100)
                        st.write(f"{idx}. **{brand}**: {count} ({percentage:.1f}%)")
            else:
                st.info("📊 Нет данных о товарах")
            
            st.divider()
            
            # Статус товаров
            st.markdown("### 📊 Статус товаров")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "✅ С ценами",
                    len(products_with_prices),
                    help="Товары готовые к продаже"
                )
            
            with col2:
                without_prices = len(products) - len(products_with_prices)
                st.metric(
                    "⚠️ Без цен",
                    without_prices,
                    help="Требуется установить цены"
                )
            
            with col3:
                # Подсчет товаров со скидками
                with_discounts = sum(1 for p in products_with_prices if p.get('discount', 0) > 0)
                st.metric(
                    "🏷️ Со скидками",
                    with_discounts,
                    help="Товары с активными скидками"
                )
            
            st.divider()
            
            # Рекомендации
            st.markdown("### 💡 Рекомендации")
            
            if without_prices > 0:
                st.warning(f"⚠️ **{without_prices} товаров без цен.** Установите цены для увеличения ассортимента.")
            
            if coverage < 50:
                st.error("❌ **Низкая готовность к продаже.** Требуется синхронизация цен.")
            elif coverage < 80:
                st.info("📊 **Хорошая готовность.** Рекомендуется синхронизировать оставшиеся товары.")
            else:
                st.success("✅ **Отличная готовность!** Большинство товаров готовы к продаже.")
        
        # =============================================================================
        # ШАБЛОН: ЮНИТ-ЭКОНОМИКА (ЦЕНЫ)
        # =============================================================================
        elif dashboard_template == "💰 Юнит-экономика":
            st.markdown("### 💰 Юнит-экономика и ценообразование")
            
            if products_with_prices:
                # Основные метрики цен
                col1, col2, col3, col4 = st.columns(4)
                
                total_price = sum(p.get('price', 0) or 0 for p in products_with_prices)
                avg_price = total_price / len(products_with_prices)
                avg_discount = sum(p.get('discount', 0) or 0 for p in products_with_prices) / len(products_with_prices)
                avg_attractive = sum(p.get('attractive_price', 0) or 0 for p in products_with_prices) / len([p for p in products_with_prices if p.get('attractive_price')])
                
                with col1:
                    st.metric("💵 Средняя цена", f"{avg_price:,.2f} ₽")
                with col2:
                    st.metric("🏷️ Средняя скидка", f"{avg_discount:.1f}%")
                with col3:
                    st.metric("✨ Привлек. цена", f"{avg_attractive:,.2f} ₽" if avg_attractive else "-")
                with col4:
                    st.metric("📊 Товаров с ценами", len(products_with_prices))
                
                st.divider()
                
                # Расчет маржинальности (упрощенный)
                st.markdown("### 📊 Анализ маржинальности")
                
                st.info("💡 **Формула маржи**: (Цена - Себестоимость - Комиссия WB - Логистика) / Цена × 100%")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("📈 Средняя маржа", "-", help="Будет рассчитана после добавления себестоимости")
                with col2:
                    st.metric("💰 Комиссия WB", "~5-15%", help="Зависит от категории (с июня 2025 +5%)")
                with col3:
                    st.metric("🎯 ROI", "-", help="Рентабельность инвестиций")
                
                st.divider()
                
                # Распределение цен
                st.markdown("### 📊 Распределение цен")
                
                prices = [p.get('price', 0) or 0 for p in products_with_prices]
                
                if prices:
                    price_ranges = {
                        "До 500 ₽": len([p for p in prices if p < 500]),
                        "500-1000 ₽": len([p for p in prices if 500 <= p < 1000]),
                        "1000-2000 ₽": len([p for p in prices if 1000 <= p < 2000]),
                        "2000-5000 ₽": len([p for p in prices if 2000 <= p < 5000]),
                        "5000+ ₽": len([p for p in prices if p >= 5000]),
                    }
                    
                    st.bar_chart(price_ranges)
                
                st.divider()
                
                # Топ по маржинальности (упрощенно по скидкам)
                st.markdown("### 💎 Товары с максимальной скидкой")
                
                top_discounts = sorted(products_with_prices, key=lambda x: x.get('discount', 0) or 0, reverse=True)[:10]
                
                discount_data = []
                for item in top_discounts:
                    discount_data.append({
                        'Бренд': item.get('brand', 'N/A'),
                        'Артикул': item.get('vendor_code', 'N/A'),
                        'Цена': f"{item.get('price', 0):,.2f} ₽",
                        'Скидка': f"{item.get('discount', 0)}%"
                    })
                
                st.dataframe(discount_data, use_container_width=True, hide_index=True)
            
            else:
                st.warning("📊 Нет данных о ценах. Выполните синхронизацию цен.")
        
        # =============================================================================
        # ШАБЛОН: ФИНАНСЫ (ОПиУ)
        # =============================================================================
        elif dashboard_template == "💼 Финансы (ОПиУ)":
            st.markdown("### 💼 Финансовый отчет (ОПиУ)")
            
            if products_with_prices:
                # Расчет базовых финансовых показателей на основе данных
                total_price_value = sum(p.get('price', 0) or 0 for p in products_with_prices)
                total_discounted = sum(p.get('discounted_price', 0) or 0 for p in products_with_prices)
                avg_discount = sum(p.get('discount', 0) or 0 for p in products_with_prices) / len(products_with_prices)
                
                # Потенциальная выручка (если все товары будут проданы по 1 шт)
                potential_revenue = total_discounted if total_discounted > 0 else total_price_value
                
                # Оценка затрат (примерная комиссия WB 5-15%, берем 10%)
                wb_commission = potential_revenue * 0.10
                
                # Примерная логистика (2-5% от выручки)
                logistics_cost = potential_revenue * 0.03
                
                # Оценка маржи
                estimated_margin = ((potential_revenue - wb_commission - logistics_cost) / potential_revenue * 100) if potential_revenue > 0 else 0
                
                # Основные финансовые показатели
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "💰 Потенциальная выручка",
                        f"{potential_revenue:,.0f} ₽",
                        help="Сумма цен всех товаров (при продаже по 1 шт)"
                    )
                with col2:
                    st.metric(
                        "💸 Комиссия WB",
                        f"{wb_commission:,.0f} ₽",
                        help="Примерная комиссия маркетплейса (~10%)"
                    )
                with col3:
                    st.metric(
                        "📈 Чистая выручка",
                        f"{potential_revenue - wb_commission - logistics_cost:,.0f} ₽",
                        help="После вычета комиссий и логистики"
                    )
                with col4:
                    st.metric(
                        "📊 Оценочная маржа",
                        f"{estimated_margin:.1f}%",
                        help="Приблизительная маржинальность"
                    )
                
                st.divider()
                
                # Структура затрат
                st.markdown("### 📊 Структура затрат (оценочно)")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "🏪 Комиссия WB",
                        f"{wb_commission:,.0f} ₽",
                        f"~{(wb_commission/potential_revenue*100):.1f}%",
                        help="Комиссия маркетплейса"
                    )
                with col2:
                    st.metric(
                        "🚚 Логистика",
                        f"{logistics_cost:,.0f} ₽",
                        f"~{(logistics_cost/potential_revenue*100):.1f}%",
                        help="Доставка и возвраты (оценка)"
                    )
                with col3:
                    total_costs = wb_commission + logistics_cost
                    st.metric(
                        "💸 Всего затрат",
                        f"{total_costs:,.0f} ₽",
                        f"~{(total_costs/potential_revenue*100):.1f}%",
                        help="Сумма всех затрат"
                    )
                
                st.divider()
                
                # Анализ по ценовым сегментам
                st.markdown("### 💎 Анализ по ценовым сегментам")
                
                # Разделение на сегменты
                premium = [p for p in products_with_prices if (p.get('price', 0) or 0) >= 5000]
                mid_range = [p for p in products_with_prices if 1000 <= (p.get('price', 0) or 0) < 5000]
                budget = [p for p in products_with_prices if (p.get('price', 0) or 0) < 1000]
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    premium_value = sum(p.get('price', 0) or 0 for p in premium)
                    st.metric(
                        "💎 Премиум (5000+ ₽)",
                        f"{len(premium)} шт",
                        f"{premium_value:,.0f} ₽",
                        help="Товары дороже 5000 ₽"
                    )
                
                with col2:
                    mid_value = sum(p.get('price', 0) or 0 for p in mid_range)
                    st.metric(
                        "📊 Средний (1000-5000 ₽)",
                        f"{len(mid_range)} шт",
                        f"{mid_value:,.0f} ₽",
                        help="Товары от 1000 до 5000 ₽"
                    )
                
                with col3:
                    budget_value = sum(p.get('price', 0) or 0 for p in budget)
                    st.metric(
                        "💰 Бюджет (<1000 ₽)",
                        f"{len(budget)} шт",
                        f"{budget_value:,.0f} ₽",
                        help="Товары дешевле 1000 ₽"
                    )
                
                st.divider()
                
                # Рекомендации
                st.markdown("### 💡 Рекомендации по финансам")
                
                if avg_discount > 30:
                    st.warning(f"⚠️ **Высокая средняя скидка ({avg_discount:.1f}%)** - проверьте целесообразность больших скидок.")
                
                if estimated_margin < 15:
                    st.error("❌ **Низкая маржинальность** - рекомендуется пересмотреть ценообразование или снизить затраты.")
                elif estimated_margin < 25:
                    st.info("📊 **Нормальная маржинальность** - есть пространство для оптимизации.")
                else:
                    st.success("✅ **Хорошая маржинальность!** Продолжайте в том же духе.")
                
                st.info("""
                **📝 Примечание:** Расчеты являются оценочными и основаны на имеющихся данных о ценах.
                Для точного ОПиУ необходима интеграция с финансовыми отчетами WB API.
                """)
            
            else:
                st.warning("📊 Нет данных о ценах. Выполните синхронизацию цен для расчета финансовых показателей.")
        
        # =============================================================================
        # ШАБЛОН: ЛОГИСТИКА
        # =============================================================================
        elif dashboard_template == "🚚 Логистика":
            st.markdown("### 🚚 Логистика и склад")
            st.info("🚧 Функционал логистики будет добавлен после интеграции Warehouse API")
            
            # Метрики склада
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📦 На складе WB", "-", help="Текущие остатки")
            with col2:
                st.metric("🚚 В пути", "-", help="Товары в транзите")
            with col3:
                st.metric("📐 Объем (литры)", "-", help="Суммарный литраж")
            with col4:
                st.metric("⏱️ Средний срок", "-", help="Дней на складе")
            
            st.divider()
            
            st.markdown("### 💰 Стоимость логистики")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("💸 Хранение (день)", "-", help="Стоимость за день")
            with col2:
                st.metric("📥 Приемка", "-", help="Стоимость приемки")
            with col3:
                st.metric("↩️ Возвраты", "-", help="Стоимость возвратной логистики")
            
            st.divider()
            
            st.markdown("### 📊 Оборачиваемость по категориям")
            
            st.info("Будет доступно после синхронизации остатков и продаж")
    
    except Exception as e:
        st.error(f"❌ Ошибка загрузки данных: {e}")

# =============================================================================
# СИНХРОНИЗАЦИЯ
# =============================================================================
elif page == "🔄 Синхронизация":
    st.title("🔄 Синхронизация данных")

    # Инициализируем session state
    if not init_session_state():
        st.error("❌ БД не подключена. Проверьте настройки.")
        st.stop()

    if not st.session_state.db_connected:
        st.error("❌ БД не подключена. Проверьте настройки.")
        st.stop()
    
    st.markdown("""
    Синхронизация данных из WB API в базу данных.
    - **Артикулы**: Content Cards API → БД
    - **Цены**: Discounts-Prices API → БД
    """)
    
    st.divider()
    
    # Артикулы
    st.subheader("📦 Синхронизация артикулов")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        max_cards = st.number_input(
            "Максимум карточек (0 = все)",
            min_value=0,
            value=100,
            step=50,
            help="Для теста используйте небольшое значение"
        )
    
    with col2:
        st.write("")
        st.write("")
        sync_articles_btn = st.button("▶️ Запустить", key="sync_articles", type="primary")
    
    if sync_articles_btn:
        with st.spinner("Синхронизация артикулов..."):
            try:
                from wb_api.content_cards import WBContentCardsClient, API_KEY
                
                # Проверяем, что API ключ настроен
                if not API_KEY or API_KEY == "your_wildberries_api_key_here":
                    st.error("❌ API ключ не настроен!")
                    st.warning("""
                    **Необходимо настроить API ключ:**
                    1. Откройте файл `api_keys.py`
                    2. Замените `WB_API_KEY = "your_wildberries_api_key_here"`
                    3. На реальный ключ из личного кабинета WB
                    
                    **Где взять ключ:**
                    - Зайдите в личный кабинет поставщика Wildberries
                    - Перейдите: **Настройки → Доступ к API**
                    - Создайте новый токен с правами на **Content/Контент**
                    - Скопируйте и вставьте в `api_keys.py`
                    """)
                    st.stop()
                
                api_client = WBContentCardsClient(API_KEY)
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("Загрузка данных из WB API...")
                progress_bar.progress(30)
                
                stats = sync_content_cards_to_db(
                    api_client=api_client,
                    db_client=st.session_state.db_client,
                    max_cards=max_cards if max_cards > 0 else None
                )
                
                progress_bar.progress(100)
                status_text.text("Готово!")
                
                time.sleep(0.5)
                progress_bar.empty()
                status_text.empty()
                
                if stats['failed'] == 0:
                    st.success(f"✅ Синхронизация завершена успешно!")
                else:
                    st.warning(f"⚠️ Синхронизация завершена с ошибками")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Успешно", stats['success'])
                with col2:
                    st.metric("Ошибок", stats['failed'])
                with col3:
                    st.metric("Всего баркодов", stats['total_variants'])
            
            except Exception as e:
                st.error(f"❌ Ошибка: {e}")
                if "401" in str(e) or "Unauthorized" in str(e):
                    st.warning("""
                    **Ошибка авторизации (401 Unauthorized)**
                    
                    Возможные причины:
                    1. API ключ неверный или устарел
                    2. API ключ не имеет прав на работу с контентом
                    3. Истек срок действия токена
                    
                    **Решение:**
                    - Создайте новый токен в личном кабинете WB
                    - Убедитесь, что у токена есть права на **Content/Контент**
                    - Обновите `WB_API_KEY` в `api_keys.py`
                    """)
    
    st.divider()
    
    # Цены
    st.subheader("💰 Синхронизация цен")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        max_goods = st.number_input(
            "Максимум товаров (0 = все)",
            min_value=0,
            value=50,
            step=50,
            help="Для теста используйте небольшое значение"
        )
    
    with col2:
        st.write("")
        st.write("")
        sync_prices_btn = st.button("▶️ Запустить", key="sync_prices", type="primary")
    
    if sync_prices_btn:
        with st.spinner("Синхронизация цен..."):
            try:
                from wb_api.discounts_prices.discounts_prices import WBDiscountsPricesClient, AUTHORIZEV3_TOKEN
                
                # Проверяем, что API ключ настроен
                if not AUTHORIZEV3_TOKEN or AUTHORIZEV3_TOKEN == "your_discounts_api_key_here":
                    st.error("❌ API ключ для цен не настроен!")
                    st.warning("""
                    **Необходимо настроить API ключ для цен:**
                    1. Откройте файл `api_keys.py`
                    2. Замените `WB_DISCOUNTS_API_KEY = "your_discounts_api_key_here"`
                    3. На реальный ключ из личного кабинета WB
                    
                    **Где взять ключ:**
                    - Зайдите в личный кабинет поставщика Wildberries
                    - Перейдите: **Настройки → Доступ к API**
                    - Создайте новый токен с правами на **Цены и скидки**
                    - Скопируйте и вставьте в `api_keys.py`
                    """)
                    st.stop()
                
                api_client = WBDiscountsPricesClient()
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("Загрузка данных из WB API...")
                progress_bar.progress(30)
                
                stats = sync_discounts_prices_to_db(
                    api_client=api_client,
                    db_client=st.session_state.db_client,
                    max_goods=max_goods if max_goods > 0 else None
                )
                
                progress_bar.progress(100)
                status_text.text("Готово!")
                
                time.sleep(0.5)
                progress_bar.empty()
                status_text.empty()
                
                if stats['failed'] == 0:
                    st.success(f"✅ Синхронизация завершена успешно!")
                else:
                    st.warning(f"⚠️ Синхронизация завершена с ошибками")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Успешно", stats['success'])
                with col2:
                    st.metric("Ошибок", stats['failed'])
            
            except Exception as e:
                st.error(f"❌ Ошибка: {e}")
                if "401" in str(e) or "Unauthorized" in str(e):
                    st.warning("""
                    **Ошибка авторизации (401 Unauthorized)**
                    
                    Возможные причины:
                    1. API ключ неверный или устарел
                    2. API ключ не имеет прав на работу с ценами
                    3. Истек срок действия токена
                    
                    **Решение:**
                    - Создайте новый токен в личном кабинете WB
                    - Убедитесь, что у токена есть права на **Цены и скидки**
                    - Обновите `WB_DISCOUNTS_API_KEY` в `api_keys.py`
                    """)

# =============================================================================
# ТОВАРЫ
# =============================================================================
elif page == "📦 Товары":
    st.title("📦 Товары")

    # Инициализируем session state
    if not init_session_state():
        st.error("❌ БД не подключена. Проверьте настройки.")
        st.stop()

    if not st.session_state.db_connected:
        st.error("❌ БД не подключена. Проверьте настройки.")
        st.stop()

    db = st.session_state.db_client
    
    # Фильтры
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_nm_id = st.text_input("🔍 Поиск по nmID", placeholder="12345678")
    
    with col2:
        search_vendor = st.text_input("🔍 Поиск по артикулу продавца", placeholder="ART-001")
    
    with col3:
        search_brand = st.text_input("🔍 Поиск по бренду", placeholder="MyBrand")
    
    # Загрузка данных
    try:
        products = db.get_active_products()
        
        # Фильтрация
        if search_nm_id:
            products = [p for p in products if str(p.get('nm_id', '')).startswith(search_nm_id)]
        if search_vendor:
            products = [p for p in products if search_vendor.lower() in str(p.get('vendor_code', '')).lower()]
        if search_brand:
            products = [p for p in products if search_brand.lower() in str(p.get('brand', '')).lower()]
        
        st.info(f"Найдено товаров: {len(products)}")
        
        if products:
            # Конвертация в DataFrame
            df = pd.DataFrame(products)
            
            # Выбор колонок для отображения
            display_columns = ['nm_id', 'vendor_code', 'brand', 'title', 'subject', 'volume', 'updated_at']
            available_columns = [col for col in display_columns if col in df.columns]
            
            if 'updated_at' in df.columns:
                df['updated_at'] = pd.to_datetime(df['updated_at']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Переименование колонок
            column_names = {
                'nm_id': 'nmID',
                'vendor_code': 'Артикул',
                'brand': 'Бренд',
                'title': 'Название',
                'subject': 'Категория',
                'volume': 'Литраж',
                'updated_at': 'Обновлено'
            }
            
            df_display = df[available_columns].rename(columns=column_names)
            
            # Отображение таблицы
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True
            )
            
            # Детали товара
            st.divider()
            st.subheader("🔍 Детали товара")
            
            selected_nm_id = st.selectbox(
                "Выберите товар",
                options=[p['nm_id'] for p in products],
                format_func=lambda x: f"{x} - {next((p['brand'] for p in products if p['nm_id'] == x), 'N/A')}"
            )
            
            if selected_nm_id:
                # Информация о товаре
                product = next((p for p in products if p['nm_id'] == selected_nm_id), None)
                if product:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Основная информация**")
                        st.write(f"**nmID:** {product.get('nm_id')}")
                        st.write(f"**Артикул:** {product.get('vendor_code')}")
                        st.write(f"**Бренд:** {product.get('brand')}")
                        st.write(f"**Категория:** {product.get('subject')}")
                    
                    with col2:
                        st.markdown("**Дополнительно**")
                        st.write(f"**Литраж:** {product.get('volume', 0)} л")
                        st.write(f"**Активен:** {'Да' if product.get('active') else 'Нет'}")
                        st.write(f"**Обновлено:** {product.get('updated_at')}")
                    
                    # Баркоды
                    st.markdown("**Баркоды и размеры**")
                    barcodes = db.get_active_barcodes(nm_id=selected_nm_id)
                    if barcodes:
                        barcodes_df = pd.DataFrame(barcodes)
                        st.dataframe(
                            barcodes_df[['barcode', 'size']].rename(columns={
                                'barcode': 'Штрихкод',
                                'size': 'Размер'
                            }),
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("Нет баркодов")
        
        else:
            st.info("Товары не найдены")
    
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")

# =============================================================================
# ЦЕНЫ
# =============================================================================
elif page == "💰 Цены":
    st.title("💰 Цены и скидки")

    # Инициализируем session state
    if not init_session_state():
        st.error("❌ БД не подключена. Проверьте настройки.")
        st.stop()

    if not st.session_state.db_connected:
        st.error("❌ БД не подключена. Проверьте настройки.")
        st.stop()

    db = st.session_state.db_client
    
    # Фильтры
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_competitive = st.checkbox("Только с конкурентной ценой")
    
    with col2:
        filter_promotions = st.checkbox("Только с промо-акциями")
    
    with col3:
        min_discount = st.slider("Минимальная скидка (%)", 0, 100, 0)
    
    # Загрузка данных
    try:
        products = db.get_products_with_prices()
        
        # Фильтрация
        if filter_competitive:
            products = [p for p in products if p.get('is_competitive_price')]
        if filter_promotions:
            products = [p for p in products if p.get('has_promotions')]
        if min_discount > 0:
            products = [p for p in products if (p.get('discount', 0) or 0) >= min_discount]
        
        st.info(f"Найдено товаров: {len(products)}")
        
        if products:
            # Конвертация в DataFrame
            df = pd.DataFrame(products)
            
            # Выбор колонок
            display_columns = [
                'nm_id', 'vendor_code', 'brand', 'price', 'discounted_price',
                'discount', 'discount_on_site', 'price_after_spp', 'competitive_price'
            ]
            available_columns = [col for col in display_columns if col in df.columns]
            
            # Переименование
            column_names = {
                'nm_id': 'nmID',
                'vendor_code': 'Артикул',
                'brand': 'Бренд',
                'price': 'Цена',
                'discounted_price': 'Со скидкой',
                'discount': 'Скидка %',
                'discount_on_site': 'СПП %',
                'price_after_spp': 'После СПП',
                'competitive_price': 'Конкурентная'
            }
            
            df_display = df[available_columns].rename(columns=column_names)
            
            # Форматирование чисел
            for col in ['Цена', 'Со скидкой', 'После СПП', 'Конкурентная']:
                if col in df_display.columns:
                    df_display[col] = df_display[col].apply(lambda x: f"{x:.2f}" if x and x != 99999 else "-")
            
            # Отображение
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True
            )
            
            # Статистика
            st.divider()
            st.subheader("📊 Статистика")
            
            col1, col2, col3, col4 = st.columns(4)
            
            prices = [p.get('price', 0) or 0 for p in products if p.get('price')]
            discounts = [p.get('discount', 0) or 0 for p in products if p.get('discount')]
            
            with col1:
                if prices:
                    st.metric("Средняя цена", f"{sum(prices) / len(prices):.2f} ₽")
                else:
                    st.metric("Средняя цена", "-")
            
            with col2:
                if discounts:
                    st.metric("Средняя скидка", f"{sum(discounts) / len(discounts):.1f}%")
                else:
                    st.metric("Средняя скидка", "-")
            
            with col3:
                competitive_count = sum(1 for p in products if p.get('is_competitive_price'))
                st.metric("С конкурентной ценой", competitive_count)
            
            with col4:
                promo_count = sum(1 for p in products if p.get('has_promotions'))
                st.metric("С промо-акциями", promo_count)
        
        else:
            st.info("Товары не найдены")
    
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")

# =============================================================================
# ИСТОРИЯ ЦЕН
# =============================================================================
elif page == "📈 История цен":
    st.title("📈 История изменения цен")

    # Инициализируем session state
    if not init_session_state():
        st.error("❌ БД не подключена. Проверьте настройки.")
        st.stop()

    if not st.session_state.db_connected:
        st.error("❌ БД не подключена. Проверьте настройки.")
        st.stop()
    
    st.info("📌 Функция в разработке. Используйте SQL-запросы из database/queries.sql")

# =============================================================================
# ЛОГИ
# =============================================================================
elif page == "📝 Логи":
    st.title("📝 Логи операций")

    # Инициализируем session state
    if not init_session_state():
        st.error("❌ БД не подключена. Проверьте настройки.")
        st.stop()

    if not st.session_state.db_connected:
        st.error("❌ БД не подключена. Проверьте настройки.")
        st.stop()

    db = st.session_state.db_client
    
    # Количество записей
    limit = st.slider("Количество записей", 10, 100, 20, step=10)
    
    try:
        logs = db.get_recent_logs(limit=limit)
        
        if logs:
            df = pd.DataFrame(logs)
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Фильтр по статусу
            status_filter = st.multiselect(
                "Фильтр по статусу",
                options=['success', 'warning', 'error'],
                default=['success', 'warning', 'error'],
                format_func=lambda x: {'success': '✅ Успешно', 'warning': '⚠️ Предупреждение', 'error': '❌ Ошибка'}[x]
            )
            
            if status_filter:
                df = df[df['status'].isin(status_filter)]
            
            # Отображение
            st.dataframe(
                df[['timestamp', 'operation_type', 'status', 'records_processed', 'records_failed', 'execution_time_ms']].rename(columns={
                    'timestamp': 'Время',
                    'operation_type': 'Операция',
                    'status': 'Статус',
                    'records_processed': 'Обработано',
                    'records_failed': 'Ошибок',
                    'execution_time_ms': 'Время (мс)'
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Нет записей в логах")
    
    except Exception as e:
        st.error(f"Ошибка загрузки логов: {e}")

# =============================================================================
# SQL ЗАПРОСЫ
# =============================================================================
elif page == "🔧 SQL Запросы":
    st.title("🔧 SQL Запросы")
    
    st.markdown("""
    Готовые SQL-запросы для работы с базой данных.
    Используйте их в Python-коде или выполняйте напрямую через Supabase.
    """)
    
    st.divider()
    
    # Категории запросов
    query_category = st.selectbox(
        "📋 Категория запросов",
        [
            "🔍 Основные выборки",
            "➕ Upsert артикулов",
            "💰 Upsert цен",
            "📊 Аналитика и отчеты",
            "🗑️ Очистка и обслуживание"
        ]
    )
    
    # =============================================================================
    # ОСНОВНЫЕ ВЫБОРКИ
    # =============================================================================
    if query_category == "🔍 Основные выборки":
        st.subheader("🔍 Основные выборки данных")
        
        # Запрос 1: Активные товары
        with st.expander("📦 Все активные товары"):
            st.code("""
-- Получить все активные товары
SELECT 
    p.nm_id,
    p.vendor_code,
    p.brand,
    p.title,
    p.subject,
    p.volume,
    p.updated_at
FROM products p
WHERE p.is_active = TRUE
ORDER BY p.updated_at DESC;
            """, language="sql")
            
            st.markdown("**Использование в Python:**")
            st.code("""
products = db.client.table('products') \\
    .select('*') \\
    .eq('is_active', True) \\
    .order('updated_at', desc=True) \\
    .execute()
            """, language="python")
        
        # Запрос 2: Товары с ценами
        with st.expander("💰 Товары с ценами"):
            st.code("""
-- Получить товары с ценами
SELECT 
    p.nm_id,
    p.vendor_code,
    p.brand,
    p.title,
    ue.price,
    ue.discounted_price,
    ue.discount,
    ue.competitive_price,
    ue.updated_at as price_updated_at
FROM products p
INNER JOIN unit_economics ue ON p.nm_id = ue.nm_id
WHERE p.is_active = TRUE
ORDER BY ue.price DESC;
            """, language="sql")
            
            st.markdown("**Использование в Python:**")
            st.code("""
products_with_prices = db.get_products_with_prices()
            """, language="python")
        
        # Запрос 3: Активные баркоды
        with st.expander("🏷️ Активные баркоды"):
            st.code("""
-- Получить все активные баркоды с товарами
SELECT 
    sa.barcode,
    sa.vendor_code,
    sa.size,
    p.brand,
    p.title,
    sa.updated_at
FROM seller_articles sa
INNER JOIN products p ON sa.nm_id = p.nm_id
WHERE sa.is_active = TRUE
ORDER BY sa.updated_at DESC;
            """, language="sql")
            
            st.markdown("**Использование в Python:**")
            st.code("""
barcodes = db.get_active_barcodes()
            """, language="python")
    
    # =============================================================================
    # UPSERT АРТИКУЛОВ
    # =============================================================================
    elif query_category == "➕ Upsert артикулов":
        st.subheader("➕ Upsert артикулов из Content API")
        
        # Запрос 1: Upsert товара
        with st.expander("📦 Upsert одного товара"):
            st.code("""
-- Вставка/обновление товара
INSERT INTO products (nm_id, vendor_code, brand, title, subject, volume)
VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT (nm_id) DO UPDATE SET
    vendor_code = EXCLUDED.vendor_code,
    brand = EXCLUDED.brand,
    title = EXCLUDED.title,
    subject = EXCLUDED.subject,
    volume = EXCLUDED.volume,
    updated_at = NOW()
RETURNING id, nm_id;
            """, language="sql")
            
            st.markdown("**Использование в Python:**")
            st.code("""
from database.db_client import get_client

db = get_client()
result = db.upsert_product(
    nm_id=12345678,
    vendor_code='ART-001',
    brand='MyBrand',
    title='Товар 1',
    subject='Футболки',
    volume=0.5
)
            """, language="python")
        
        # Запрос 2: Batch upsert
        with st.expander("📦 Batch upsert товаров"):
            st.code("""
-- Массовая вставка/обновление товаров
INSERT INTO products (nm_id, vendor_code, brand, title, subject, volume)
VALUES 
    (12345678, 'ART-001', 'MyBrand', 'Товар 1', 'Футболки', 0.5),
    (23456789, 'ART-002', 'MyBrand', 'Товар 2', 'Кроссовки', 1.2),
    (34567890, 'ART-003', 'MyBrand', 'Товар 3', 'Рюкзаки', 2.0)
ON CONFLICT (nm_id) DO UPDATE SET
    vendor_code = EXCLUDED.vendor_code,
    brand = EXCLUDED.brand,
    title = EXCLUDED.title,
    subject = EXCLUDED.subject,
    volume = EXCLUDED.volume,
    updated_at = NOW();
            """, language="sql")
        
        # Запрос 3: Upsert баркодов
        with st.expander("🏷️ Upsert баркодов"):
            st.code("""
-- Вставка/обновление баркода
INSERT INTO seller_articles (nm_id, vendor_code, barcode, size)
VALUES ($1, $2, $3, $4)
ON CONFLICT (barcode) DO UPDATE SET
    nm_id = EXCLUDED.nm_id,
    vendor_code = EXCLUDED.vendor_code,
    size = EXCLUDED.size,
    updated_at = NOW()
RETURNING id, barcode;
            """, language="sql")
            
            st.markdown("**Batch upsert:**")
            st.code("""
-- Массовая вставка баркодов
INSERT INTO seller_articles (nm_id, vendor_code, barcode, size)
VALUES 
    (12345678, 'ART-001', '2000000123456', 'M'),
    (12345678, 'ART-001', '2000000123457', 'L'),
    (23456789, 'ART-002', '2000000234567', '42')
ON CONFLICT (barcode) DO UPDATE SET
    nm_id = EXCLUDED.nm_id,
    vendor_code = EXCLUDED.vendor_code,
    size = EXCLUDED.size,
    updated_at = NOW();
            """, language="sql")
    
    # =============================================================================
    # UPSERT ЦЕН
    # =============================================================================
    elif query_category == "💰 Upsert цен":
        st.subheader("💰 Upsert цен из Discounts-Prices API")
        
        # Запрос 1: Upsert цен
        with st.expander("💰 Upsert цен одного товара"):
            st.code("""
-- Вставка/обновление цен
INSERT INTO unit_economics (
    nm_id, vendor_code, price, discounted_price, discount, 
    discount_on_site, price_after_spp, competitive_price, 
    is_competitive_price, has_promotions
)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
ON CONFLICT (nm_id) DO UPDATE SET
    vendor_code = EXCLUDED.vendor_code,
    price = EXCLUDED.price,
    discounted_price = EXCLUDED.discounted_price,
    discount = EXCLUDED.discount,
    discount_on_site = EXCLUDED.discount_on_site,
    price_after_spp = EXCLUDED.price_after_spp,
    competitive_price = EXCLUDED.competitive_price,
    is_competitive_price = EXCLUDED.is_competitive_price,
    has_promotions = EXCLUDED.has_promotions,
    updated_at = NOW()
RETURNING nm_id, price_after_spp;
            """, language="sql")
        
        # Запрос 2: История цен
        with st.expander("📈 Добавление в историю цен"):
            st.code("""
-- Сохранение истории изменения цен
INSERT INTO price_history (
    nm_id, vendor_code, price, discounted_price, 
    discount, competitive_price
)
VALUES ($1, $2, $3, $4, $5, $6)
RETURNING id, nm_id, changed_at;
            """, language="sql")
            
            st.markdown("**Использование в Python:**")
            st.code("""
# Автоматически добавляется при обновлении цен через триггер
db.upsert_unit_economics(
    nm_id=12345678,
    price=1000.0,
    discounted_price=900.0,
    discount=10
)
# История создастся автоматически
            """, language="python")
    
    # =============================================================================
    # АНАЛИТИКА
    # =============================================================================
    elif query_category == "📊 Аналитика и отчеты":
        st.subheader("📊 Аналитические запросы")
        
        # Запрос 1: Топ по ценам
        with st.expander("💰 Топ-10 самых дорогих товаров"):
            st.code("""
-- Топ-10 товаров по цене
SELECT 
    p.nm_id,
    p.vendor_code,
    p.brand,
    p.title,
    ue.price,
    ue.discount
FROM products p
INNER JOIN unit_economics ue ON p.nm_id = ue.nm_id
WHERE p.is_active = TRUE
ORDER BY ue.price DESC
LIMIT 10;
            """, language="sql")
        
        # Запрос 2: Средние показатели
        with st.expander("📊 Средние показатели по ценам"):
            st.code("""
-- Средние показатели
SELECT 
    COUNT(*) as total_products,
    AVG(ue.price) as avg_price,
    AVG(ue.discount) as avg_discount,
    MAX(ue.price) as max_price,
    MIN(ue.price) as min_price
FROM unit_economics ue
INNER JOIN products p ON ue.nm_id = p.nm_id
WHERE p.is_active = TRUE;
            """, language="sql")
        
        # Запрос 3: История изменения цен
        with st.expander("📈 История изменения цен товара"):
            st.code("""
-- История изменения цен конкретного товара
SELECT 
    ph.changed_at,
    ph.price,
    ph.discounted_price,
    ph.discount,
    ph.competitive_price
FROM price_history ph
WHERE ph.nm_id = $1
ORDER BY ph.changed_at DESC
LIMIT 30;
            """, language="sql")
            
            st.markdown("**Использование в Python:**")
            st.code("""
history = db.get_price_history(nm_id=12345678, limit=30)
            """, language="python")
    
    # =============================================================================
    # ОЧИСТКА
    # =============================================================================
    elif query_category == "🗑️ Очистка и обслуживание":
        st.subheader("🗑️ Очистка и обслуживание БД")
        
        # Запрос 1: Очистка логов
        with st.expander("🧹 Очистка старых логов"):
            st.code("""
-- Удалить логи старше 30 дней
DELETE FROM validation_logs
WHERE timestamp < NOW() - INTERVAL '30 days'
RETURNING id;
            """, language="sql")
            
            st.markdown("**Использование в Python:**")
            st.code("""
deleted_count = db.cleanup_old_logs(days=30)
print(f"Удалено записей: {deleted_count}")
            """, language="python")
        
        # Запрос 2: Очистка истории цен
        with st.expander("🧹 Очистка старой истории цен"):
            st.code("""
-- Удалить историю цен старше 90 дней
DELETE FROM price_history
WHERE changed_at < NOW() - INTERVAL '90 days'
RETURNING id;
            """, language="sql")
            
            st.markdown("**Использование в Python:**")
            st.code("""
deleted_count = db.cleanup_old_price_history(days=90)
print(f"Удалено записей: {deleted_count}")
            """, language="python")
        
        # Запрос 3: Деактивация товаров
        with st.expander("📦 Деактивация неактивных товаров"):
            st.code("""
-- Деактивировать товары, не обновлявшиеся более 30 дней
UPDATE products
SET is_active = FALSE
WHERE updated_at < NOW() - INTERVAL '30 days'
  AND is_active = TRUE
RETURNING nm_id, vendor_code;
            """, language="sql")
    
    st.divider()
    
    # Ссылка на полный файл
    st.markdown("### 📄 Полный файл запросов")
    st.info("Все SQL-запросы доступны в файле: `database/queries.sql` (567 строк)")
    
    st.markdown("""
    **Содержит:**
    - Upsert артикулов и баркодов
    - Upsert цен и истории
    - Аналитические запросы
    - Функции агрегации
    - Триггеры и процедуры
    - Примеры использования в Python
    """)

# =============================================================================
# НАСТРОЙКИ
# =============================================================================
elif page == "⚙️ Настройки":
    st.title("⚙️ Настройки и обслуживание")

    # Инициализируем session state
    if not init_session_state():
        st.error("❌ БД не подключена. Проверьте настройки.")
        st.stop()

    if not st.session_state.db_connected:
        st.error("❌ БД не подключена. Проверьте настройки.")
        st.stop()

    db = st.session_state.db_client
    
    # Очистка данных
    st.subheader("🗑️ Очистка старых данных")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Очистка логов (>30 дней)**")
        if st.button("🧹 Очистить логи", type="secondary"):
            with st.spinner("Очистка..."):
                try:
                    deleted = db.cleanup_old_logs()
                    st.success(f"✅ Удалено записей: {deleted}")
                except Exception as e:
                    st.error(f"❌ Ошибка: {e}")
    
    with col2:
        st.markdown("**Очистка истории цен (>90 дней)**")
        if st.button("🧹 Очистить историю", type="secondary"):
            with st.spinner("Очистка..."):
                try:
                    deleted = db.cleanup_old_price_history()
                    st.success(f"✅ Удалено записей: {deleted}")
                except Exception as e:
                    st.error(f"❌ Ошибка: {e}")
    
    st.divider()
    
    # Информация о подключении
    st.subheader("ℹ️ Информация о подключении")
    
    st.code(f"""
URL: {db.url}
Key: {db.key[:20]}...{db.key[-20:]}
    """)
    
    st.divider()
    
    # Ссылки на документацию
    st.subheader("📚 Документация")
    
    st.markdown("""
    - [database/README.md](./database/README.md) - Полная документация
    - [database/SETUP.md](./database/SETUP.md) - Инструкция по настройке
    - [database/queries.sql](./database/queries.sql) - SQL запросы
    - [Supabase Dashboard](https://app.supabase.com)
    """)
