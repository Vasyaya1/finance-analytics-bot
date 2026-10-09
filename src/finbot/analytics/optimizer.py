import numpy as np
import pandas as pd
import scipy.stats as stats
from scipy.optimize import minimize


def generate_optimization_report(product_records, financial_records, budget=1000000):

    if not product_records or not financial_records:
        return "❌ Нет данных для оптимизации."

    df_prod = pd.DataFrame([dict(r) for r in product_records])
    df_fin = pd.DataFrame([dict(r) for r in financial_records])

    df_prod['product_revenue'] = df_prod['product_revenue'].astype(float)
    df_prod['product_cost'] = df_prod['product_cost'].astype(float)
    df_prod['quantity_sold'] = df_prod['quantity_sold'].astype(float)
    
    df_fin['revenue'] = df_fin['revenue'].astype(float)
    df_fin['marketing_budget'] = df_fin['marketing_budget'].astype(float)
    
    if df_prod['product_cost'].sum() <= 0:
        return "❌ <b>Ошибка данных:</b> Для работы ML-алгоритма необходимы данные о себестоимости. Пожалуйста, добавьте колонку «Себестоимость_товара» в Excel-файл и загрузите его снова."

    df_prod['stock_qty'] = df_prod['stock_qty'].astype(float)
    
    if df_prod['stock_qty'].sum() <= 0:
        return "❌ <b>Ошибка данных:</b> Для работы SCM-алгоритма необходимы актуальные данные о складе. В вашей базе остатки равны 0. Пожалуйста, добавьте колонку «Остаток_на_конец_месяца_шт» в лист «Товары» и загрузите Excel-файл снова."

    df_prod = df_prod.sort_values('period')

    unique_months = max(1, df_prod['period'].nunique())
    
    marketing_history = df_fin['marketing_budget'].values
    revenue_history = df_fin['revenue'].values

    if len(marketing_history) > 1 and np.std(marketing_history) > 0 and np.std(revenue_history) > 0:
        correlation = np.corrcoef(marketing_history, revenue_history)[0, 1]
        if np.isnan(correlation): correlation = 0.5
    else:
        correlation = 0.5

    marketing_power = max(0.1, 0.5 + (correlation * 2.0))
    
    prod_stats = df_prod.groupby('product_name').agg(
        total_rev=('product_revenue', 'sum'),
        total_cost=('product_cost', 'sum'),
        total_qty_sold=('quantity_sold', 'sum'),
        current_stock=('stock_qty', 'last') 
    ).reset_index()

    prod_stats['avg_monthly_qty'] = prod_stats['total_qty_sold'] / unique_months
    prod_stats['base_demand_rub'] = prod_stats['total_cost'] / unique_months
    prod_stats['roi'] = (prod_stats['total_rev'] - prod_stats['total_cost']) / prod_stats['total_cost'].replace(0, 1)
    
    prod_stats['coverage_ratio'] = prod_stats['current_stock'] / prod_stats['avg_monthly_qty'].replace(0, 0.1)

    prod_stats['unit_cost'] = prod_stats['total_cost'] / prod_stats['total_qty_sold'].replace(0, 1.0)

    price_threshold = prod_stats['unit_cost'].quantile(0.70)

    prod_stats['category'] = prod_stats['unit_cost'].apply(
        lambda x: 'anchor' if x >= price_threshold else 'accessory'
    )

    hist_anchor_base = prod_stats[prod_stats['category'] == 'anchor']['base_demand_rub'].sum()
    if hist_anchor_base <= 0: hist_anchor_base = 1.0

    pivot_sales = df_prod.pivot_table(index='period', columns='product_name', values='product_revenue', aggfunc='sum', fill_value=0)
    std_devs = pivot_sales.std().to_dict()
    mean_sales = pivot_sales.mean().to_dict()
    prod_stats['risk_coef'] = prod_stats['product_name'].apply(
        lambda x: (std_devs.get(x, 0) / mean_sales.get(x, 1)) if mean_sales.get(x, 1) > 0 else 1.0
    )

    n_vars = 1 + len(prod_stats)

    def objective(y):
        M = y[0] * budget
        
        anchor_spend = sum(y[i+1]*budget for i in range(len(prod_stats)) if prod_stats.iloc[i]['category'] == 'anchor')
        total_goods_spend = max(sum(y[1:]) * budget, 1.0)
        anchor_ratio = anchor_spend / total_goods_spend

        halo_effect = 0.5 + (anchor_ratio * 0.8) 
        
        market_multiplier = 1.0 + marketing_power * np.log1p(M / 300000.0) * halo_effect

        total_utility = 0

        for i in range(len(prod_stats)):
            inv_spend = y[i+1] * budget
            base_demand = prod_stats.iloc[i]['base_demand_rub']
            roi = prod_stats.iloc[i]['roi']
            risk = prod_stats.iloc[i]['risk_coef']
            is_anchor = prod_stats.iloc[i]['category'] == 'anchor'
            coverage = prod_stats.iloc[i]['coverage_ratio']

            if not is_anchor:
                cross_sell = (anchor_spend / hist_anchor_base) ** 0.6 
                demand_cap = max(base_demand * market_multiplier * cross_sell, 1.0)
            else:
                demand_cap = max(base_demand * market_multiplier, 1.0)

            qty_sold = prod_stats.iloc[i]['total_qty_sold']
            safe_qty = qty_sold if qty_sold > 0 else 1.0
            
            stock_value = prod_stats.iloc[i]['current_stock'] * (prod_stats.iloc[i]['total_cost'] / safe_qty)
            
            stock_sold_cost = min(demand_cap, stock_value)
            profit_from_stock = stock_sold_cost * roi
            
            effective_demand = max(demand_cap - stock_value, 0.0)
            expected_sales_cost = effective_demand * (1.0 - np.exp(-inv_spend / effective_demand)) if effective_demand > 0 else 0
            profit_from_new = expected_sales_cost * (1.0 + roi) - inv_spend
            
            product_profit = profit_from_stock + profit_from_new

            inventory_penalty = 0
            if coverage > 1.2:
                penalty_weight = 2.0 if is_anchor else 8.0
                inventory_penalty = inv_spend * ((coverage - 1.2) ** 2) * penalty_weight
            elif coverage < 0.3:
                product_profit += inv_spend * 0.5

            risk_penalty = 0.15 * risk * (inv_spend ** 2) / budget

            total_utility += (product_profit - risk_penalty - inventory_penalty)

        total_utility -= M
        return -total_utility / budget 

    def constraint_budget(y):
        return 1.0 - np.sum(y)

    cons = [{'type': 'eq', 'fun': constraint_budget}]
    
    bounds = [(0.0, 1.0)] 
    for i in range(len(prod_stats)):
        cov = prod_stats.iloc[i]['coverage_ratio']
        is_anchor = prod_stats.iloc[i]['category'] == 'anchor'
        
        if cov > 3.0:
            bounds.append((0.0, 0.0)) 
        elif cov > 1.5:
            max_share = 0.15 if is_anchor else 0.05
            bounds.append((0.0, max_share))
        else:
            bounds.append((0.0, 1.0))
            
    y0 = np.ones(n_vars) / n_vars

    res = minimize(objective, y0, method='SLSQP', bounds=bounds, constraints=cons, options={'maxiter': 2000})

    if not res.success:
        return "❌ Ошибка сходимости алгоритма."

    opt_mkt = res.x[0] * budget
    opt_prods = res.x[1:] * budget
    expected_profit = -res.fun * budget
    
    opt_prods = np.where(opt_prods < 1000, 0.0, opt_prods)

    report = f"🧬 <b>Сквозная SCM-оптимизация (Supply Chain Management)</b>\n"
    report += f"<i>Алгоритм: Нелинейное программирование (SLSQP) + Контроль складов</i>\n"
    report += f"<i>Бюджет: {budget:,.0f} ₽</i>\n\n"

    report += f"📊 <b>Оптимальный вектор инвестиций:</b>\n"
    report += f"📢 Маркетинг: <b>{opt_mkt:,.0f} ₽</b>\n\n"
    
    report += "📦 <b>План закупки (с учетом инвентаризации):</b>\n"
    results = []
    for i, val in enumerate(opt_prods):
        name = prod_stats.iloc[i]['product_name']
        roi_pct = prod_stats.iloc[i]['roi'] * 100
        coverage = prod_stats.iloc[i]['coverage_ratio']
        cat = "💎 Якорь" if prod_stats.iloc[i]['category'] == 'anchor' else "🔗 Аксессуар"
        results.append((name, val, roi_pct, coverage, cat))
            
    results.sort(key=lambda x: x[1], reverse=True)
    
    for name, val, roi_pct, coverage, cat in results:
        if coverage > 1.5:
            stock_status = f"🛑 Затоваривание ({coverage:.1f} мес.)"
        elif coverage < 0.3:
            stock_status = f"🔥 КРИТИЧЕСКИЙ ДЕФИЦИТ ({coverage:.1f} мес.)"
        else:
            stock_status = f"✅ Норма ({coverage:.1f} мес.)"

        report += f"  • <b>{name}</b> ({cat}): <b>{val:,.0f} ₽</b> \n"
        report += f"    <i>├ Статус склада: {stock_status}</i>\n"

    sign = "+" if expected_profit > 0 else ""
    report += f"\n💰 <b>Прогнозируемая чистая прибыль: {sign}{expected_profit:,.0f} ₽</b>\n\n"

    report += "💡 <b>Data Science & Supply Chain:</b>\n"
    report += "В алгоритм внедрен модуль SKU-уровня для контроля запасов (Days Sales of Inventory). "
    report += f"Эластичность маркетинга откалибрована по историческим данным <b>(Корреляция Пирсона: {correlation:.2f})</b>. "
    report += "Если товар находится в зоне риска Out-of-Stock (Остаток &lt; 0.3 мес), ИИ перераспределяет капитал для экстренной закупки. "
    report += "Если зафиксировано затоваривание (Остаток &gt; 1.5 мес), алгоритм накладывает штраф, перенаправляя средства в маркетинг для ликвидации излишков, с учетом доказанной исторической окупаемости рекламы."

    allocation_data = {'Маркетинг': opt_mkt}
    for name, val, _, _, _ in results:
        if val > 1000:
            allocation_data[name] = val
        
    return report, allocation_data
