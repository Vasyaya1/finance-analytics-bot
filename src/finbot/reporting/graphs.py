import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import matplotlib.ticker as ticker
import numpy as np
import scipy.stats as stats

def generate_dashboard_graphs(records):

    periods = [r['period'].strftime('%m.%y') for r in records]
    revenues = np.array([float(r['revenue']) for r in records])
    fixed_costs = np.array([float(r['fixed_costs']) for r in records])
    var_costs = np.array([float(r['variable_costs']) for r in records])
    marketing = np.array([float(r['marketing_budget']) for r in records])
    taxes = np.array([float(r['taxes']) for r in records])
    new_customers = np.array([int(r['new_customers']) for r in records])
    
    ebitdas = revenues - fixed_costs - var_costs - marketing
    profits = ebitdas - taxes
    
    ros = np.zeros_like(revenues)
    mask = revenues > 0
    ros[mask] = (profits[mask] / revenues[mask]) * 100

    cac = np.zeros_like(marketing)
    mask_nc = new_customers > 0
    cac[mask_nc] = marketing[mask_nc] / new_customers[mask_nc]

    bep = np.zeros_like(revenues)
    margin_ratio = np.zeros_like(revenues)
    margin_ratio[mask] = (revenues[mask] - var_costs[mask]) / revenues[mask]
    mask_margin = margin_ratio > 0
    bep[mask_margin] = (fixed_costs[mask_margin] + marketing[mask_margin]) / margin_ratio[mask_margin]

    fig, axs = plt.subplots(3, 2, figsize=(14, 15))
    fig.suptitle('Комплексный Финансовый Дашборд', fontsize=18, fontweight='bold')
    
    def money_format(x, pos):
        return f"{int(x):,}".replace(',', ' ')

    axs[0, 0].plot(periods, revenues, marker='o', color='#1f77b4', linewidth=2.5, label='Выручка')
    axs[0, 0].plot(periods, profits, marker='s', color='#2ca02c', linewidth=2.5, label='Чистая прибыль')
    axs[0, 0].set_title('Динамика выручки и прибыли', fontsize=12, fontweight='bold')
    axs[0, 0].grid(True, linestyle='--', alpha=0.7)
    axs[0, 0].legend()
    axs[0, 0].tick_params(axis='x', rotation=45)
    axs[0, 0].yaxis.set_major_formatter(ticker.FuncFormatter(money_format))

    colors = np.where(ros > 0, '#2ca02c', '#d62728')
    bars = axs[0, 1].bar(periods, ros, color=colors, alpha=0.8)
    axs[0, 1].set_title('Рентабельность продаж (ROS, %)', fontsize=12, fontweight='bold')
    axs[0, 1].axhline(0, color='black', linewidth=1)
    axs[0, 1].grid(True, linestyle='--', alpha=0.7, axis='y')
    axs[0, 1].tick_params(axis='x', rotation=45)
    
    axs[1, 0].bar(periods, fixed_costs, label='Постоянные', color='#ff7f0e')
    axs[1, 0].bar(periods, var_costs, bottom=fixed_costs, label='Переменные', color='#1f77b4')
    axs[1, 0].bar(periods, marketing, bottom=fixed_costs+var_costs, label='Маркетинг', color='#9467bd')
    axs[1, 0].set_title('Структура расходов', fontsize=12, fontweight='bold')
    axs[1, 0].grid(True, linestyle='--', alpha=0.7, axis='y')
    axs[1, 0].legend()
    axs[1, 0].tick_params(axis='x', rotation=45)
    axs[1, 0].yaxis.set_major_formatter(ticker.FuncFormatter(money_format))

    if len(profits) >= 3:
        mean_np = np.mean(profits)
        std_np = np.std(profits, ddof=1)
        x = np.linspace(mean_np - 4*std_np, mean_np + 4*std_np, 1000)
        y = stats.norm.pdf(x, mean_np, std_np)
        
        axs[1, 1].plot(x, y, color='#ff7f0e', linewidth=2)
        axs[1, 1].fill_between(x, y, where=(x < 0), color='red', alpha=0.4, label='Зона убытка (Риск)')
        axs[1, 1].fill_between(x, y, where=(x >= 0), color='green', alpha=0.1, label='Зона прибыли')
        axs[1, 1].axvline(mean_np, color='black', linestyle='dashed', label=f'Мат. ожидание: {mean_np:,.0f}')
        axs[1, 1].set_title('Плотность распределения прибыли', fontsize=12, fontweight='bold')
        axs[1, 1].legend(loc='upper right')
        axs[1, 1].grid(True, linestyle='--', alpha=0.5)
        axs[1, 1].xaxis.set_major_formatter(ticker.FuncFormatter(money_format))
    else:
        axs[1, 1].text(0.5, 0.5, 'Для графика рисков нужно\nминимум 3 месяца данных.', ha='center', va='center', fontsize=12)
        axs[1, 1].axis('off')

    axs[2, 0].plot(periods, cac, marker='D', color='#d62728', linewidth=2)
    axs[2, 0].set_title('Стоимость привлечения клиента (CAC)', fontsize=12, fontweight='bold')
    axs[2, 0].grid(True, linestyle='--', alpha=0.7)
    axs[2, 0].tick_params(axis='x', rotation=45)
    axs[2, 0].yaxis.set_major_formatter(ticker.FuncFormatter(money_format))
    axs[2, 0].set_ylabel('Руб. за 1 клиента')

    axs[2, 1].plot(periods, revenues, marker='o', color='#1f77b4', linewidth=2, label='Выручка')
    axs[2, 1].plot(periods, bep, marker='x', color='#7f7f7f', linewidth=2, linestyle='--', label='Точка безубыточности (BEP)')
    
    axs[2, 1].fill_between(periods, bep, revenues, where=(revenues >= bep), color='green', alpha=0.2, label='Запас прочности')
    axs[2, 1].fill_between(periods, bep, revenues, where=(revenues < bep), color='red', alpha=0.2, label='Зона убытка')
    
    axs[2, 1].set_title('Запас финансовой прочности', fontsize=12, fontweight='bold')
    axs[2, 1].grid(True, linestyle='--', alpha=0.7)
    axs[2, 1].legend()
    axs[2, 1].tick_params(axis='x', rotation=45)
    axs[2, 1].yaxis.set_major_formatter(ticker.FuncFormatter(money_format))

    plt.tight_layout(rect=[0, 0, 1, 0.97])

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300)
    buf.seek(0)
    plt.close()
    
    return buf

def generate_optimization_pie_chart(allocation_data):
    if not allocation_data:
        return None
        
    data = {k: v for k, v in allocation_data.items() if v > 0}
    if not data:
        return None
        
    labels = list(data.keys())
    sizes = list(data.values())
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Функция для вывода и процентов, и точной суммы в рублях на графике
    def make_autopct(values):
        def my_autopct(pct):
            total = sum(values)
            val = int(round(pct * total / 100.0))
            return f'{pct:.1f}%\n({val:,} ₽)'.replace(',', ' ')
        return my_autopct

    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct=make_autopct(sizes), 
        startangle=140, colors=plt.cm.Set3.colors,
        textprops=dict(color="black", fontsize=10)
    )
    
    plt.setp(autotexts, size=9, weight="bold")
    
    total_budget_str = f"{sum(sizes):,.0f} ₽".replace(',', ' ')
    ax.set_title(f'Оптимальный вектор инвестиций (ML)\nРаспределение бюджета: {total_budget_str}', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300)
    buf.seek(0)
    plt.close(fig)
    return buf

def generate_anomaly_scatter_plot(records, anomaly_flags):
    if not records or not anomaly_flags:
        return None
        
    revenues = [float(r['revenue']) for r in records]
    marketing = [float(r['marketing_budget']) for r in records]
    var_costs = [float(r['variable_costs']) for r in records]
    periods = [r['period'].strftime('%m.%y') for r in records]
    
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    for i in range(len(records)):
        x, y, z = marketing[i], var_costs[i], revenues[i]
        if anomaly_flags[i] == 1:
            ax.scatter(x, y, z, c='#1f77b4', s=60, alpha=0.5)
        else:
            ax.scatter(x, y, z, c='#d62728', s=150, marker='X', depthshade=False)
            ax.text(x, y, z * 1.05, periods[i], color='red', fontweight='bold', fontsize=10)
            
    ax.plot([], [], 'o', color='#1f77b4', markersize=8, label='Норма')
    ax.plot([], [], 'X', color='#d62728', markersize=10, label='Аномалия')
    ax.legend(loc='upper left')
    
    def money_format(x, pos):
        return f"{int(x/1000)}k"

    ax.xaxis.set_major_formatter(ticker.FuncFormatter(money_format))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(money_format))
    ax.zaxis.set_major_formatter(ticker.FuncFormatter(money_format))
    
    ax.set_xlabel('Маркетинг (руб)', fontweight='bold')
    ax.set_ylabel('Переменные (руб)', fontweight='bold')
    ax.set_zlabel('Выручка (руб)', fontweight='bold')
    ax.set_title('3D-Детекция аномалий (Isolation Forest)', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300)
    buf.seek(0)
    plt.close(fig)
    return buf
