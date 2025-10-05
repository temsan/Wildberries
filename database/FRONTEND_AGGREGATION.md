# 📊 Агрегация цен на фронте

## 🎯 Стратегия: минимальные данные в БД + агрегация на фронте

### 💡 Логика:
- Храним только базовые данные о ценах
- Все метрики и агрегации считаем на фронте
- Максимальная гибкость анализа

## 🏗️ Упрощенная структура БД

```sql
-- Минимальные данные для агрегации на фронте
CREATE TABLE unit_economics (
    id BIGSERIAL PRIMARY KEY,
    nm_id INTEGER NOT NULL REFERENCES products(nm_id),
    recorded_at TIMESTAMP DEFAULT NOW(),
    
    -- Только базовые данные
    price DECIMAL(10,2),           -- Базовая цена
    discounted_price DECIMAL(10,2), -- Цена со скидкой
    discount INTEGER,              -- Скидка (%)
    discount_on_site INTEGER       -- СПП (%)
);
```

## 📊 Агрегации на фронте

### 1. Базовые метрики:
```javascript
const calculateMetrics = (priceData) => {
    return {
        price_after_spp: priceData.discounted_price * (1 - priceData.discount_on_site / 100),
        savings: priceData.price - priceData.discounted_price,
        total_discount: ((priceData.price - priceData.discounted_price) / priceData.price) * 100,
        is_competitive: priceData.discount > 10
    };
};
```

### 2. Агрегация по времени:
```javascript
const aggregateByPeriod = (data, period = 'day') => {
    return data.reduce((acc, item) => {
        const key = new Date(item.recorded_at).toISOString().split('T')[0];
        if (!acc[key]) {
            acc[key] = { avg_price: 0, min_price: Infinity, max_price: 0, count: 0 };
        }
        acc[key].avg_price += item.price;
        acc[key].min_price = Math.min(acc[key].min_price, item.price);
        acc[key].max_price = Math.max(acc[key].max_price, item.price);
        acc[key].count++;
        return acc;
    }, {});
};
```

### 3. Агрегация по брендам/категориям:
```javascript
const aggregateByBrand = (data, products) => {
    return data.reduce((acc, item) => {
        const product = products.find(p => p.nm_id === item.nm_id);
        const brand = product?.brand || 'Unknown';
        
        if (!acc[brand]) {
            acc[brand] = { total_revenue: 0, avg_price: 0, count: 0 };
        }
        acc[brand].total_revenue += item.price;
        acc[brand].avg_price += item.price;
        acc[brand].count++;
        return acc;
    }, {});
};
```

## 🚀 API для фронта

### Минимальный endpoint:
```python
@app.get("/api/prices/{nm_id}")
async def get_prices(nm_id: int, days: int = 30):
    """Возвращает базовые данные цен для агрегации на фронте"""
    prices = db.query("""
        SELECT price, discounted_price, discount, discount_on_site, recorded_at
        FROM unit_economics 
        WHERE nm_id = %s AND recorded_at >= NOW() - INTERVAL '%s days'
        ORDER BY recorded_at DESC
    """, [nm_id, days])
    
    return {"prices": prices}
```

## 📈 Преимущества:

1. **Гибкость** - любые агрегации на фронте
2. **Простота БД** - минимум данных
3. **Быстрые запросы** - простая структура
4. **Масштабируемость** - нагрузка на клиент
5. **Отладка** - данные как есть

## 🎯 Результат:
Минимальная БД + максимальная гибкость анализа на фронте!
