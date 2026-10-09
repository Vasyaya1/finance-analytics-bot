import logging

from aiogram import Bot

from finbot.db import database


async def send_weekly_summary(bot_instance: Bot):
    users = await database.get_all_users()
    for user in users:
        telegram_id = user['telegram_id']
        try:
            records = await database.get_financial_records(telegram_id)
            if not records:
                await bot_instance.send_message(
                    telegram_id,
                    "👋 <b>Напоминание:</b> Вы еще не загрузили финансовые данные. Отправьте мне Excel-отчет, чтобы я мог построить графики и аналитику!",
                    parse_mode="HTML"
                )
                continue
                
            latest_record = records[-1]
            period_str = latest_record['period'].strftime('%m.%Y')
            rev = float(latest_record['revenue'])
            expenses = float(latest_record['fixed_costs']) + float(latest_record['variable_costs']) + float(latest_record['marketing_budget'])
            
            msg = f"📊 <b>Ваша финансовая сводка (актуальный месяц: {period_str}):</b>\n\n"
            msg += f"💵 Выручка: <b>{rev:,.0f} ₽</b>\n"
            msg += f"📉 Расходы: <b>{expenses:,.0f} ₽</b>\n\n"
            
            if expenses > rev and rev > 0:
                msg += "🚨 <b>Алерт:</b> Ваши расходы превышают выручку! Рекомендуем провести глубокий анализ (кнопка в меню).\n\n"
                
            msg += "💡 Не забудьте загрузить отчет за новый месяц или внести быстрые транзакции!"
            
            await bot_instance.send_message(telegram_id, msg, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Ошибка при отправке сводки пользователю {telegram_id}: {e}")
