from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Загрузить Excel отчет", callback_data="upload_data")],
        [InlineKeyboardButton(text="➕ Быстрая операция (Чек)", callback_data="add_micro_transaction")],
        [InlineKeyboardButton(text="📊 Аналитика и тренды", callback_data="show_analytics")],
        [InlineKeyboardButton(text="📦 ABC-анализ товаров", callback_data="abc_analysis")],
        [InlineKeyboardButton(text="🔮 Прогноз и риски (Что если?)", callback_data="what_if_scenario")],
        [InlineKeyboardButton(text="🧬 Глубокий анализ (Риски и Юнит)", callback_data="advanced_analytics")],
        [InlineKeyboardButton(text="🎯 Оптимизация бюджета (ML)", callback_data="optimize_budget")],
        [InlineKeyboardButton(text="🕵️ Поиск аномалий (ML)", callback_data="find_anomalies")],
        [InlineKeyboardButton(text="📈 Графики (Визуализация)", callback_data="show_graphs")],
        [InlineKeyboardButton(text="📄 Выгрузить отчет (PDF)", callback_data="export_pdf")]
    ])
    return keyboard
