import pandas as pd
from sklearn.ensemble import IsolationForest


def detect_anomalies(records):
    if len(records) < 6:
        return "❌ Для корректной работы алгоритма Isolation Forest нужно минимум 6 месяцев исторических данных."

    df = pd.DataFrame([dict(r) for r in records])
    df['revenue'] = df['revenue'].astype(float)
    df['variable_costs'] = df['variable_costs'].astype(float)
    df['marketing_budget'] = df['marketing_budget'].astype(float)

    model = IsolationForest(contamination=0.1, random_state=42)
    features = df[['revenue', 'variable_costs', 'marketing_budget']]
    
    df['anomaly'] = model.fit_predict(features)
    anomalies = df[df['anomaly'] == -1]
    
    report = f"🌲 <b>Поиск аномалий (Isolation Forest)</b>\n"
    report += f"<i>Проанализировано месяцев: {len(df)}</i>\n\n"
    
    mean_rev = df['revenue'].mean()
    mean_mkt = df['marketing_budget'].mean()
    mean_vc = df['variable_costs'].mean()
    
    valid_anomalies = []
    for idx, row in anomalies.iterrows():
        r_diff = abs(((row['revenue'] / mean_rev) - 1) * 100) if mean_rev > 0 else 0
        m_diff = abs(((row['marketing_budget'] / mean_mkt) - 1) * 100) if mean_mkt > 0 else 0
        v_diff = abs(((row['variable_costs'] / mean_vc) - 1) * 100) if mean_vc > 0 else 0
        if r_diff > 15 or m_diff > 15 or v_diff > 15:
            valid_anomalies.append(idx)
            
    df.loc[~df.index.isin(valid_anomalies), 'anomaly'] = 1
    anomalies = df[df['anomaly'] == -1]

    if anomalies.empty:
        report += "✅ <b>Аномалий не найдено.</b> Финансовые потоки ведут себя стабильно (колебания в пределах нормы).\n"
        return report, df['anomaly'].tolist()
    
    report += f"🚨 <b>Обнаружено подозрительных месяцев: {len(anomalies)}</b>\n\n"
    
    for _, row in anomalies.iterrows():
        period_str = row['period'].strftime('%m.%Y')
        
        rev_diff = ((row['revenue'] / mean_rev) - 1) * 100 if mean_rev > 0 else 0
        mkt_diff = ((row['marketing_budget'] / mean_mkt) - 1) * 100 if mean_mkt > 0 else 0
        vc_diff = ((row['variable_costs'] / mean_vc) - 1) * 100 if mean_vc > 0 else 0
        
        report += f"📅 <b>{period_str}</b>\n"
        report += "<b>Детализация отклонений:</b>\n"
        report += f"💵 Выручка: {row['revenue']:,.0f} ₽ (<i>{'+' if rev_diff>0 else ''}{rev_diff:.0f}% от нормы</i>)\n"
        report += f"📢 Маркетинг: {row['marketing_budget']:,.0f} ₽ (<i>{'+' if mkt_diff>0 else ''}{mkt_diff:.0f}% от нормы</i>)\n"
        report += f"📦 Закупка (Переменные): {row['variable_costs']:,.0f} ₽ (<i>{'+' if vc_diff>0 else ''}{vc_diff:.0f}% от нормы</i>)\n"
        
        if row['marketing_budget'] > mean_mkt * 1.5 and row['revenue'] < mean_rev:
            report += "<i>⚠️ Гипотеза ИИ: Токсичный маркетинг (Слив бюджета без роста продаж).</i>\n\n"
        elif row['revenue'] > mean_rev * 1.5 and row['marketing_budget'] <= mean_mkt:
            report += "<i>🔥 Гипотеза ИИ: Взрывной органический рост (Вирусный эффект / Хайп).</i>\n\n"
        elif row['variable_costs'] > row['revenue']:
             report += "<i>🚨 Гипотеза ИИ: Жесткий кассовый разрыв (Переменные расходы сожрали выручку).</i>\n\n"
        elif row['revenue'] > mean_rev * 1.3 and row['marketing_budget'] > mean_mkt * 1.3:
            report += "<i>📈 Гипотеза ИИ: Сезонный пик / Агрессивное масштабирование (Синхронный взлет расходов и доходов).</i>\n\n"
        else:
            report += "<i>🔍 Гипотеза ИИ: Нетипичное соотношение метрик. Требует ручной проверки.</i>\n\n"
            
    report += "💡 <b>Справка:</b> Алгоритм Unsupervised ML нашел эти точки, так как их \"физика\" сильно отклоняется от вашей нормы."
    
    return report, df['anomaly'].tolist()
