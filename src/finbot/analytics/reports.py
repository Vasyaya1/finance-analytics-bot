import numpy as np
import pandas as pd
import scipy.stats as stats


def generate_basic_analytics_report(records):

    if not records:
        return "❌ Нет данных для анализа."

    report = "📊 <b>Финансовая аналитика (последние периоды)</b>\n\n"
    
    for row in records[-3:]:
        period_str = row['period'].strftime('%m.%Y')
        rev = float(row['revenue'])
        fc = float(row['fixed_costs'])
        vc = float(row['variable_costs'])
        taxes = float(row['taxes'])
        marketing = float(row['marketing_budget'])
        
        ebitda = rev - fc - vc - marketing
        net_profit = ebitda - taxes
        ros = (net_profit / rev * 100) if rev > 0 else 0
        
        report += f"📅 <b>Период: {period_str}</b>\n"
        report += f"💵 Выручка: {rev:,.0f} ₽\n"
        report += f"📈 EBITDA: {ebitda:,.0f} ₽\n"
        report += f"💰 Чистая прибыль: {net_profit:,.0f} ₽\n"
        report += f"📊 Рентабельность (ROS): {ros:.2f}%\n"
        report += "〰️〰️〰️〰️〰️〰️〰️\n"
        
    if len(records) >= 2:
        last = records[-1]
        prev = records[-2]
        
        def calc_metrics(row):
            rev = float(row['revenue'])
            ebitda = rev - float(row['fixed_costs']) - float(row['variable_costs']) - float(row['marketing_budget'])
            np = ebitda - float(row['taxes'])
            ros_val = (np / rev * 100) if rev > 0 else 0
            return ros_val, np
            
        last_ros, last_np = calc_metrics(last)
        prev_ros, prev_np = calc_metrics(prev)
        
        report += "\n💡 <b>Автоматические рекомендации (сравнение последних 2-х месяцев):</b>\n"
        
        if last_np < 0:
            report += "🚨 <b>Критический риск:</b> Зафиксирован убыток! Срочно проанализируйте переменные расходы и эффективность маркетингового бюджета. Рассмотрите отказ от товаров категории C.\n"
        elif last_ros < prev_ros:
            report += f"⚠️ <b>Внимание:</b> Рентабельность продаж упала ({prev_ros:.1f}% ➡️ {last_ros:.1f}%). Возможно, выросла себестоимость, либо упал средний чек. Рекомендуется пересмотреть ценообразование.\n"
        elif last_ros > 20:
            report += "✅ <b>Отлично:</b> Высокая рентабельность (>20%). Бизнес работает эффективно. Рассмотрите возможность реинвестирования части прибыли в маркетинг для масштабирования.\n"
        else:
            report += "ℹ️ <b>Стабильность:</b> Показатели в пределах нормы. Продолжайте контролировать постоянные издержки для удержания маржинальности.\n"
            
    elif len(records) == 1:
        report += "\n💡 <i>Загрузите данные хотя бы за 2 периода, чтобы система могла отслеживать тренды и формировать рекомендации.</i>\n"

    return report

def generate_abc_report(product_records, financial_records):
    if not product_records or not financial_records:
        return "❌ Нет данных для проведения ABC-анализа ассортимента."
    
    df_prod = pd.DataFrame([dict(r) for r in product_records])
    df_fin = pd.DataFrame([dict(r) for r in financial_records])
    
    df_prod['period'] = pd.to_datetime(df_prod['period'])
    start_period = df_prod['period'].min()
    latest_period = df_prod['period'].max()
    
    df_prod['product_revenue'] = df_prod['product_revenue'].astype(float)
    df_prod['product_cost'] = df_prod['product_cost'].astype(float)
    
    grouped = df_prod.groupby('product_name', as_index=False)[['product_revenue', 'product_cost']].sum()
    
    has_cost_data = grouped['product_cost'].sum() > 0
    
    grouped['product_profit'] = grouped['product_revenue'] - grouped['product_cost']
    
    total_revenue_sum = grouped['product_revenue'].sum()
    total_profit_sum = grouped['product_profit'].sum()
    
    start_str = start_period.strftime('%m.%Y')
    end_str = latest_period.strftime('%m.%Y')
    period_text = f"за {start_str}" if start_str == end_str else f"за период с {start_str} по {end_str}"
    
    if total_revenue_sum <= 0 or total_profit_sum <= 0:
        return f"📦 <b>ABC-анализ ({period_text}):</b>\n⚠️ В этом периоде финансовые показатели равны 0. Анализ невозможен."
    
    def run_abc_for_column(df, sort_col, total_sum):
        # Убыточные позиции (значение < 0) не участвуют в расчёте долей: иначе они уменьшают
        # знаменатель, и доли остальных товаров в сумме превышают 100 %.
        losers = df[df[sort_col] < 0].sort_values(by=sort_col)
        df = df[df[sort_col] >= 0]
        total_sum = df[sort_col].sum()
        df_sorted = df.sort_values(by=sort_col, ascending=False).reset_index(drop=True)
        df_sorted['share'] = (df_sorted[sort_col] / total_sum) * 100 if total_sum > 0 else 0.0
        df_sorted['cumsum'] = df_sorted['share'].cumsum()

        cats = {'A': [], 'B': [], 'C': [], 'LOSS': []}
        for idx, row in df_sorted.iterrows():
            c_sum = row['cumsum']
            val = float(row[sort_col])
            sh = float(row['share'])
            item_str = f"• {row['product_name']}: {val:,.0f} ₽ ({sh:.1f}%)"

            if c_sum <= 80 or (idx == 0 and c_sum > 80):
                cats['A'].append(item_str)
            elif c_sum <= 95:
                cats['B'].append(item_str)
            else:
                cats['C'].append(item_str)
        for _, row in losers.iterrows():
            cats['LOSS'].append(f"• {row['product_name']}: {float(row[sort_col]):,.0f} ₽")
        return cats
        
    abc_by_rev = run_abc_for_column(grouped, 'product_revenue', total_revenue_sum)
    abc_by_prof = run_abc_for_column(grouped, 'product_profit', total_profit_sum)
    
    report = f"📦 <b>Двухфакторный комплексный ABC-анализ</b>\n<i>({period_text})</i>\n\n"
    
    report += "🔹 <b>Критерий 1: Вклад в ВЫРУЧКУ (Оборот)</b>\n"
    report += "🟩 <b>Класс А</b> (до 80% кассы — локомотивы):\n" + ("\n".join(abc_by_rev['A']) if abc_by_rev['A'] else "<i>нет</i>") + "\n"
    report += "🟨 <b>Класс B</b> (80%-95% — база):\n" + ("\n".join(abc_by_rev['B']) if abc_by_rev['B'] else "<i>нет</i>") + "\n"
    report += "🟥 <b>Класс C</b> (оставшиеся 5% — балласт):\n" + ("\n".join(abc_by_prof['C']) if abc_by_prof['C'] else "<i>нет</i>") + "\n"
    if abc_by_prof['LOSS']:
        report += "⛔ <b>Убыточные</b> (продаются ниже себестоимости):\n" + "\n".join(abc_by_prof['LOSS']) + "\n"
    report += "\n"
    
    if has_cost_data:
        report += "🔹 <b>Критерий 2: Вклад в МАРЖИНАЛЬНУЮ ПРИБЫЛЬ</b>\n"
        report += "🟩 <b>Класс А</b> (до 80% маржи — кормильцы):\n" + ("\n".join(abc_by_prof['A']) if abc_by_prof['A'] else "<i>нет</i>") + "\n"
        report += "🟨 <b>Класс B</b> (80%-95% — стабильный доход):\n" + ("\n".join(abc_by_prof['B']) if abc_by_prof['B'] else "<i>нет</i>") + "\n"
        report += "🟥 <b>Класс C</b> (оставшиеся 5% — балласт):\n" + ("\n".join(abc_by_prof['C']) if abc_by_prof['C'] else "<i>нет</i>") + "\n\n"
        report += "💡 <b>Аналитическое заключение СППР:</b>\n"
        report += "Обратите внимание на товары, меняющие класс между отчетами. Товары, находящиеся в классе 🟩 <b>А по прибыли</b>, но имеющие низкий оборот, требуют масштабирования продаж. Товары из класса 🟥 <b>С по прибыли</b>, несмотря на их высокий оборот, перегружают склад и нуждаются в пересмотре цен."
    else:
        report += "🔹 <b>Критерий 2: Вклад в МАРЖИНАЛЬНУЮ ПРИБЫЛЬ</b>\n"
        report += "⚠️ <i>Данные отсутствуют. Загрузите файл со столбцом «Себестоимость_товара», чтобы система смогла рассчитать маржинальность.</i>\n\n"
        report += "💡 <b>Аналитическое заключение СППР:</b>\nДвухфакторная модель временно отключена для защиты от искажений. Анализ проведен только по обороту (Выручке)."
        
    return report

def generate_what_if_report(record):
    period_str = record['period'].strftime('%m.%Y')
    rev = float(record['revenue'])
    fc = float(record['fixed_costs'])
    vc = float(record['variable_costs'])
    taxes = float(record['taxes'])
    marketing = float(record['marketing_budget'])
    
    if rev == 0:
        return (
            f"🔮 <b>Сценарное моделирование (Что, если?)</b>\n\n"
            f"⚠️ <i>Невозможно построить прогноз на основе месяца ({period_str}), так как выручка равна 0 ₽.</i>\n\n"
            f"💡 <b>Решение:</b> Добавьте поступления выручки в этот месяц через меню «Быстрая операция»."
        )

    current_ebitda = rev - fc - vc - marketing
    current_np = current_ebitda - taxes
    current_ros = (current_np / rev * 100) if rev > 0 else 0
    
    report = f"🔮 <b>Сценарное моделирование (Что, если?)</b>\n"
    report += f"<i>Анализ на основе данных за {period_str}</i>\n\n"
    
    report += f"<b>Текущие показатели:</b>\n"
    report += f"💵 Выручка: {rev:,.0f} ₽ | 💰 Прибыль: {current_np:,.0f} ₽ ({current_ros:.1f}%)\n\n"
    
    scenarios = [
        ("🚀 Оптимистичный (+20%)", 20),
        ("📈 Умеренный рост (+10%)", 10),
        ("📉 Небольшой спад (-10%)", -10),
        ("🚨 Кризисный (-20%)", -20)
    ]
    
    analysis_data = {}
    
    for name, pct in scenarios:
        new_rev = rev * (1 + pct / 100)
        new_vc = vc * (1 + pct / 100) 
        new_taxes = taxes * (1 + pct / 100) if pct > 0 else taxes
        
        new_ebitda = new_rev - fc - new_vc - marketing
        new_np = new_ebitda - new_taxes
        new_ros = (new_np / new_rev * 100) if new_rev > 0 else 0
        diff_np = new_np - current_np
        
        if pct == 20:
            analysis_data['opt_np'] = new_np
        elif pct == -20:
            analysis_data['crisis_np'] = new_np
            
        report += f"<b>{name}:</b>\n"
        report += f"💵 Выручка: {new_rev:,.0f} ₽\n"
        report += f"💰 Прибыль: {new_np:,.0f} ₽ ({new_ros:.1f}%)\n"
        report += f"📊 Изменение прибыли: {'+' if diff_np > 0 else ''}{diff_np:,.0f} ₽\n\n"

    report += "💡 <b>Управленческое резюме (СППР):</b>\n"
    
    crisis_np = analysis_data.get('crisis_np', 0)
    opt_np = analysis_data.get('opt_np', 0)

    if crisis_np < 0:
        report += f"🚨 <b>Уязвимость к кризису:</b> При падении продаж на 20% бизнес генерирует убыток. Необходима жесткая оптимизация издержек.\n\n"
    else:
        report += f"🛡️ <b>Устойчивость:</b> Ваш бизнес стрессоустойчив! Даже при падении выручки на 20% вы остаетесь в плюсе.\n\n"

    # 2. Анализ операционного рычага
    if current_np > 0 and opt_np > 0:
        profit_growth_pct = ((opt_np - current_np) / current_np) * 100
        if profit_growth_pct > 25:
            report += f"🚀 <b>Эффект масштаба:</b> В оптимистичном сценарии выручка растет на 20%, а прибыль — на <b>{profit_growth_pct:.0f}%</b>. Направляйте свободные средства в маркетинг, каждая новая продажа приносит сверхприбыль.\n\n"
        else:
             report += f"⚖️ <b>Пропорциональный рост:</b> Ваша прибыль растет соразмерно выручке (+{profit_growth_pct:.0f}%). Для взрывного роста необходимо снижать себестоимость.\n\n"

    report += "🔍 <b>Поиск узких мест (Структура расходов):</b>\n"
    
    vc_pct = (vc / rev) * 100
    fc_pct = (fc / rev) * 100
    mkt_pct = (marketing / rev) * 100
    
    issues_found = False
    
    if vc_pct > 60:
        report += f"❌ <b>Себестоимость:</b> Переменные расходы съедают слишком много ({vc_pct:.1f}% выручки). \n<i>Решение:</i> Проведите переговоры с поставщиками о скидках за объем, либо повышайте цены на товары.\n"
        issues_found = True
        
    if fc_pct > 30:
        report += f"❌ <b>Тяжелые издержки:</b> Постоянные расходы критически высоки ({fc_pct:.1f}% выручки). \n<i>Решение:</i> Переведите часть сотрудников на сдельную оплату (KPI), откажитесь от неиспользуемых сервисов или площадей.\n"
        issues_found = True
        
    if mkt_pct > 20:
        report += f"❌ <b>Дорогой маркетинг:</b> Рекламный бюджет расходуется неэффективно ({mkt_pct:.1f}% выручки). \n<i>Решение:</i> Остановите кампании с низкой конверсией, сфокусируйтесь на удержании старых клиентов и сарафанном радио.\n"
        issues_found = True
        
    if not issues_found:
        report += "✅ <b>Все чисто:</b> Структура расходов оптимальна, явных перекосов в издержках не обнаружено.\n"

    return report

def generate_advanced_report(records):

    if len(records) < 3:
        return "❌ Для глубокого статистического анализа необходимо минимум 3 месяца данных."

    start_period_str = records[0]['period'].strftime('%m.%Y')
    end_period_str = records[-1]['period'].strftime('%m.%Y')

    report = f"🧬 <b>Глубокий статистический анализ и Риски</b>\n"
    report += f"<i>(за период с {start_period_str} по {end_period_str})</i>\n\n"
    
    revenues = np.array([float(r['revenue']) for r in records])
    marketing = np.array([float(r['marketing_budget']) for r in records])
    new_customers = np.array([int(r['new_customers']) for r in records])
    fixed_costs = np.array([float(r['fixed_costs']) for r in records])
    variable_costs = np.array([float(r['variable_costs']) for r in records])
    taxes = np.array([float(r['taxes']) for r in records])
    
    ebitdas = revenues - fixed_costs - variable_costs - marketing
    net_profits = ebitdas - taxes
    
    total_marketing = np.sum(marketing)
    total_customers = np.sum(new_customers)
    cac = total_marketing / total_customers if total_customers > 0 else 0
    
    report += "🎯 <b>Юнит-экономика:</b>\n"
    report += f"Средняя стоимость привлечения клиента (CAC): <b>{cac:,.0f} ₽</b>\n"
    if cac > 0:
        report += f"<i>(На привлечение 1 клиента вы тратите {cac:,.0f} руб. из бюджета)</i>\n\n"

    last_rev = revenues[-1]
    last_vc = variable_costs[-1]
    last_fc = fixed_costs[-1] + marketing[-1]
    
    margin_ratio = (last_rev - last_vc) / last_rev if last_rev > 0 else 0.0001
    
    report += "⚖️ <b>Точка безубыточности (BEP):</b>\n"
    if margin_ratio <= 0:
        report += "🚨 <b>Критическая ситуация:</b> Переменные расходы превышают выручку (отрицательная маржинальность)!\n"
        report += "Точка безубыточности <b>недостижима</b>. Срочно повышайте цены или снижайте себестоимость.\n\n"
    else:
        bep = last_fc / margin_ratio
        report += f"Минимальная выручка для выхода в ноль: <b>{bep:,.0f} ₽</b>\n"
        if last_rev > bep:
            report += f"✅ Запас финансовой прочности: <b>{last_rev - bep:,.0f} ₽</b>\n\n"
        else:
            report += f"🚨 Выручка ниже точки безубыточности на <b>{bep - last_rev:,.0f} ₽</b>\n\n"

    correlation = np.corrcoef(marketing, revenues)[0, 1]
    
    report += "📈 <b>Статистический анализ:</b>\n"
    report += f"Корреляция (Реклама ↔️ Выручка): <b>{correlation:.2f}</b>\n"
    if correlation > 0.7:
        report += "<i>Сильная прямая связь: увеличение бюджета на рекламу эффективно растит выручку.</i>\n\n"
    elif correlation < 0:
        report += "<i>Отрицательная связь: реклама работает неэффективно, бюджет сжигается впустую.</i>\n\n"
    else:
        report += "<i>Слабая связь: выручка зависит от других факторов (сезонность, сарафанное радио).</i>\n\n"

    mean_np = np.mean(net_profits)
    std_np = np.std(net_profits, ddof=1)
    
    prob_loss = stats.norm.cdf(0, loc=mean_np, scale=std_np) * 100
    
    report += f"🎲 <b>Вероятность кассового разрыва: {prob_loss:.1f}%</b>\n"
    report += f"<i>(Рассчитано на основе мат. ожидания {mean_np:,.0f} ₽ и стандартного отклонения {std_np:,.0f} ₽)</i>"

    return report
