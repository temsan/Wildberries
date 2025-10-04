"""
Веб-интерфейс для управления БД Wildberries (Streamlit).
Автозапуск: python database/web_interface.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from pathlib import Path
import sys

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

# Кастомные стили
st.markdown("""
    <style>
    .big-metric {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        margin: 1rem 0;
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

# Боковая панель
with st.sidebar:
    st.title("🛠️ WB API Dashboard")

    # Инициализируем session state для боковой панели
    init_session_state()

    # Статус подключения
    if st.session_state.get('db_connected', False):
        st.success("✅ БД подключена")
    else:
        st.error("❌ Ошибка подключения к БД")
        st.error(st.session_state.get('db_error', 'Неизвестная ошибка'))
        st.info("Проверьте SUPABASE_URL и SUPABASE_KEY в api_keys.py")
    
    st.divider()
    
    # Навигация
    page = st.radio(
        "Навигация",
        [
            "📊 Dashboard",
            "🔄 Синхронизация",
            "📦 Товары",
            "💰 Цены",
            "📈 История цен",
            "📝 Логи",
            "⚙️ Настройки"
        ]
    )

# =============================================================================
# DASHBOARD
# =============================================================================
if page == "📊 Dashboard":
    st.title("📊 Dashboard")

    # Инициализируем session state
    if not init_session_state():
        st.error("❌ БД не подключена. Проверьте настройки.")
        st.stop()

    if not st.session_state.db_connected:
        st.error("❌ БД не подключена. Проверьте настройки.")
        st.stop()

    db = st.session_state.db_client
    
    # Кнопка обновления
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🔄 Обновить"):
            st.rerun()
    
    # Основные метрики
    st.subheader("📈 Основные метрики")
    
    try:
        products = db.get_active_products()
        barcodes = db.get_active_barcodes()
        products_with_prices = db.get_products_with_prices()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Активных товаров", len(products))
        with col2:
            st.metric("Активных баркодов", len(barcodes))
        with col3:
            st.metric("Товаров с ценами", len(products_with_prices))
        with col4:
            coverage = (len(products_with_prices) / len(products) * 100) if products else 0
            st.metric("Покрытие ценами", f"{coverage:.1f}%")
        
        st.divider()
        
        # Последние операции
        st.subheader("📝 Последние операции")
        
        logs = db.get_recent_logs(limit=10)
        if logs:
            logs_df = pd.DataFrame(logs)
            logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Форматирование статуса
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
            st.info("Нет записей в логах")
        
        st.divider()
        
        # Топ товаров по ценам
        st.subheader("💎 Топ товаров")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Самые дорогие**")
            if products_with_prices:
                top_expensive = sorted(products_with_prices, key=lambda x: x.get('price', 0) or 0, reverse=True)[:5]
                for idx, item in enumerate(top_expensive, 1):
                    st.write(f"{idx}. {item.get('brand', 'N/A')} - {item.get('price', 0):.2f} ₽")
            else:
                st.info("Нет данных")
        
        with col2:
            st.markdown("**Максимальные скидки**")
            if products_with_prices:
                top_discounts = sorted(products_with_prices, key=lambda x: x.get('discount', 0) or 0, reverse=True)[:5]
                for idx, item in enumerate(top_discounts, 1):
                    st.write(f"{idx}. {item.get('brand', 'N/A')} - {item.get('discount', 0)}%")
            else:
                st.info("Нет данных")
    
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")

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
                from wb_api.discounts_prices.discounts_prices import WBDiscountsPricesClient
                
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


# =============================================================================
# АВТОЗАПУСК STREAMLIT
# =============================================================================
if __name__ == "__main__":
    import subprocess
    import sys
    import os

    # Автозапуск Streamlit без лишнего кода
    subprocess.run([sys.executable, "-m", "streamlit", "run", __file__], check=True)

