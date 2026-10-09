import asyncio
import logging
import os
from datetime import datetime

import pandas as pd
from aiogram import Bot, F, Router, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from finbot import analytics
from finbot.bot.keyboards import get_main_menu
from finbot.bot.states import MicroTransactionState, NLPTrainingState, OptimizeBudgetState
from finbot.db import database
from finbot.reporting import export, graphs

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    await database.add_user(user_id, username)
    
    welcome_text = (
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я — ваш финансовый ассистент. Я помогу рассчитать рентабельность, "
        "оценить риски кассового разрыва и провести анализ ассортимента.\n\n"
        "Выберите действие ниже:"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_menu())

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "📖 <b>Справка по использованию бота</b>\n\n"
        "Этот бот помогает автоматизировать анализ финансовых показателей вашего бизнеса.\n\n"
        "<b>Доступные функции:</b>\n"
        "🔹 <b>Загрузить Excel отчет</b> — отправьте файл с доходами и расходами для сохранения в базу данных.\n"
        "🔹 <b>Аналитика и тренды</b> — расчет EBITDA, чистой прибыли, ROS и других метрик.\n"
        "🔹 <b>ABC-анализ</b> — классификация товаров по их вкладу в общую выручку.\n"
        "🔹 <b>Прогноз и риски</b> — моделирование сценариев \"Что, если?\" и оценка вероятности убытков.\n\n"
        "Для вызова главного меню в любой момент используйте команду /start."
    )
    await message.answer(help_text, parse_mode="HTML")

@router.message(Command("reset_nlp"))
async def cmd_reset_nlp(message: types.Message):
    analytics.reset_nlp_dataset()
    await message.answer("🧠 <b>Память NLP-модели очищена!</b>\nВсе ваши пользовательские фразы удалены, ИИ вернулся к «заводским настройкам».", parse_mode="HTML")

@router.callback_query(F.data == "add_micro_transaction")
async def process_add_transaction(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите сумму операции (только число, например: 5000):")
    await state.set_state(MicroTransactionState.waiting_for_amount)
    await callback.answer()

@router.message(MicroTransactionState.waiting_for_amount)
async def process_transaction_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Ошибка. Введите корректное положительное число (например: 15000).")
        return

    await state.update_data(amount=amount)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Выручка (Поступили деньги)", callback_data="cat_revenue")],
        [InlineKeyboardButton(text="🏭 Постоянные расходы (Аренда, ЗП)", callback_data="cat_fixed_costs")],
        [InlineKeyboardButton(text="📦 Переменные расходы (Закупка)", callback_data="cat_variable_costs")],
        [InlineKeyboardButton(text="📢 Маркетинг (Реклама)", callback_data="cat_marketing_budget")]
    ])
    
    await message.answer(
        f"Сумма: <b>{amount:,.0f} ₽</b>.\nКуда запишем эту сумму?", 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await state.set_state(MicroTransactionState.waiting_for_category)

@router.callback_query(MicroTransactionState.waiting_for_category, F.data.startswith("cat_"))
async def process_transaction_category(callback: types.CallbackQuery, state: FSMContext):
    try:
        db_category = callback.data.replace("cat_", "")
        data = await state.get_data()
        amount = data.get('amount')
        
        await database.add_micro_transaction(callback.from_user.id, amount, db_category)
        
        category_names = {
            "revenue": "Выручка",
            "fixed_costs": "Постоянные расходы",
            "variable_costs": "Переменные расходы",
            "marketing_budget": "Маркетинг"
        }
        
        await callback.message.edit_text(
            f"✅ Успешно!\nСумма <b>{amount:,.0f} ₽</b> добавлена в категорию <b>«{category_names[db_category]}»</b> за текущий месяц.", 
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Ошибка при сохранении транзакции: {e}")
        await callback.message.answer("❌ Произошла ошибка базы данных. Пожалуйста, попробуйте еще раз.")
    finally:
        await state.clear()
        await callback.answer()

@router.callback_query(F.data == "upload_data")
async def process_upload_button(callback: types.CallbackQuery):
    await callback.message.answer("Пожалуйста, отправьте мне заполненный Excel-файл (.xlsx).")
    await callback.answer()

@router.callback_query(F.data == "show_analytics")
async def process_analytics_button(callback: types.CallbackQuery):
    records = await database.get_financial_records(callback.from_user.id)
    if not records:
        await callback.message.answer("❌ У вас пока нет данных. Пожалуйста, загрузите Excel-отчет.")
    else:
        report = analytics.generate_basic_analytics_report(records)
        await callback.message.answer(report, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "abc_analysis")
async def process_abc_button(callback: types.CallbackQuery):
    prod_records = await database.get_product_sales(callback.from_user.id)
    fin_records = await database.get_financial_records(callback.from_user.id)
    if not prod_records or not fin_records:
        await callback.message.answer("❌ У вас пока нет полных данных (нужны финансы и товары). Пожалуйста, загрузите Excel-отчет.")
    else:
        report = analytics.generate_abc_report(prod_records, fin_records)
        await callback.message.answer(report, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "what_if_scenario")
async def process_what_if_button(callback: types.CallbackQuery):
    records = await database.get_financial_records(callback.from_user.id)
    if not records:
        await callback.message.answer("❌ У вас пока нет данных. Пожалуйста, загрузите Excel-отчет.")
    else:
        latest_record = records[-1] # Берем последний месяц
        if float(latest_record['revenue']) > 0:
            report = analytics.generate_what_if_report(latest_record)
            await callback.message.answer(report, parse_mode="HTML")
        else:
            valid_record = None
            for record in reversed(records):
                if float(record['revenue']) > 0:
                    valid_record = record
                    break
                    
            if not valid_record:
                await callback.message.answer("❌ В базе нет месяцев с выручкой для построения прогноза.")
            else:
                latest_period = latest_record['period'].strftime('%m.%Y')
                report = analytics.generate_what_if_report(valid_record)
                warning = (
                    f"⚠️ <b>Внимание:</b> Выручка за <b>{latest_period}</b> равна 0 ₽. "
                    f"Так как прогнозировать рост от нулевой базы математически некорректно, система "
                    f"автоматически переключилась на ближайший прошлый месяц с реальными продажами.\n\n"
                )
                await callback.message.answer(warning + report, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "advanced_analytics")
async def process_advanced_analytics_button(callback: types.CallbackQuery):
    records = await database.get_financial_records(callback.from_user.id)
    if not records:
        await callback.message.answer("❌ У вас пока нет данных. Пожалуйста, загрузите Excel-отчет.")
    else:
        report = analytics.generate_advanced_report(records)
        await callback.message.answer(report, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "show_graphs")
async def process_graphs_button(callback: types.CallbackQuery):
    records = await database.get_financial_records(callback.from_user.id)
    if not records:
        await callback.message.answer("❌ У вас пока нет данных. Пожалуйста, загрузите Excel-отчет.")
    else:
        graph_buf = await asyncio.to_thread(graphs.generate_dashboard_graphs, records)
        photo = BufferedInputFile(graph_buf.read(), filename="dashboard.png")
        caption = (
            "📉 <b>Комплексный финансовый дашборд</b>\n\n"
            "📊 <b>1. Динамика</b> — тренд выручки и прибыли.\n"
            "📈 <b>2. Рентабельность</b> — % чистой прибыли от выручки (ROS).\n"
            "🧱 <b>3. Расходы</b> — структура постоянных и переменных затрат.\n"
            "🎲 <b>4. Риски</b> — вероятность кассового разрыва.\n"
            "🎯 <b>5. Юнит-экономика</b> — стоимость привлечения клиента (CAC).\n"
            "🛡️ <b>6. Устойчивость</b> — запас прочности и точка безубыточности (BEP)."
        )
        await callback.message.answer_photo(photo=photo, caption=caption, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "optimize_budget")
async def process_optimize_budget_button(callback: types.CallbackQuery, state: FSMContext):
    records = await database.get_financial_records(callback.from_user.id)
    if not records:
        await callback.message.answer("❌ У вас пока нет данных. Пожалуйста, загрузите Excel-отчет.")
    else:
        if len(records) < 3:
            await callback.message.answer("❌ Для работы алгоритма математической оптимизации нужно минимум 3 месяца исторических данных.")
        else:
            last_record = records[-1]
            last_np = float(last_record['revenue']) - float(last_record['fixed_costs']) - float(last_record['variable_costs']) - float(last_record['marketing_budget']) - float(last_record['taxes'])
            
            if last_np <= 0:
                await callback.message.answer("❌ Оптимизация невозможна: в последнем месяце зафиксирован убыток. Нет свободных средств для реинвестирования.")
            else:
                await callback.message.answer(
                    f"💰 В прошлом месяце ваша чистая прибыль составила <b>{last_np:,.0f} ₽</b>.\n\n"
                    "Какую долю от этой суммы (в процентах) вы готовы выделить на реинвестирование и развитие в этом месяце?\n"
                    "<i>Введите число от 1 до 100 (например: 50):</i>", 
                    parse_mode="HTML"
                )
                await state.set_state(OptimizeBudgetState.waiting_for_percent)
    await callback.answer()

@router.message(OptimizeBudgetState.waiting_for_percent)
async def process_optimize_percent(message: types.Message, state: FSMContext):
    try:
        percent = float(message.text.replace(',', '.'))
        if not (0 < percent <= 100):
            raise ValueError
    except ValueError:
        await message.answer("❌ Ошибка. Введите корректное число от 1 до 100 (например: 50).")
        return
        
    fin_records = await database.get_financial_records(message.from_user.id)
    prod_records = await database.get_product_sales(message.from_user.id)
    
    last_record = fin_records[-1]
    last_np = float(last_record['revenue']) - float(last_record['fixed_costs']) - float(last_record['variable_costs']) - float(last_record['marketing_budget']) - float(last_record['taxes'])
    budget = last_np * (percent / 100.0)
    
    report_result = analytics.generate_optimization_report(prod_records, fin_records, budget=budget)
    
    if isinstance(report_result, tuple):
        report_text, allocation_data = report_result
        await message.answer(report_text, parse_mode="HTML")
        
        graph_buf = await asyncio.to_thread(graphs.generate_optimization_pie_chart, allocation_data)
        if graph_buf:
            photo = BufferedInputFile(graph_buf.read(), filename="optimization.png")
            await message.answer_photo(photo=photo, caption="📊 <b>Визуализация распределения выделенного бюджета</b>", parse_mode="HTML")
    else:
        await message.answer(report_result, parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data == "export_pdf")
async def process_export_pdf(callback: types.CallbackQuery):
    records = await database.get_financial_records(callback.from_user.id)
    if not records:
        await callback.message.answer("❌ У вас пока нет данных. Пожалуйста, загрузите Excel-отчет.")
        await callback.answer()
        return
        
    msg = await callback.message.answer("⏳ Собираю данные и генерирую PDF-документ, это займет пару секунд...")
    
    try:
        prod_records = await database.get_product_sales(callback.from_user.id)
        
        adv_report = await asyncio.to_thread(analytics.generate_advanced_report, records)
        abc_report = await asyncio.to_thread(analytics.generate_abc_report, prod_records, records) if prod_records and records else ""
        graph_buf = await asyncio.to_thread(graphs.generate_dashboard_graphs, records)
        
        opt_text = ""
        opt_graph_buf = None
        anomaly_text = ""
        anomaly_graph_buf = None
        
        if len(records) >= 3 and prod_records:
            last_record = records[-1]
            last_np = float(last_record['revenue']) - float(last_record['fixed_costs']) - float(last_record['variable_costs']) - float(last_record['marketing_budget']) - float(last_record['taxes'])
            
            if last_np > 0:
                budget = last_np * 0.5
                opt_result = await asyncio.to_thread(analytics.generate_optimization_report, prod_records, records, budget)
                
                if isinstance(opt_result, tuple):
                    opt_text, allocation_data = opt_result
                    opt_graph_buf = await asyncio.to_thread(graphs.generate_optimization_pie_chart, allocation_data)
                else:
                    opt_text = opt_result

        if len(records) >= 6:
            anomaly_result = await asyncio.to_thread(analytics.detect_anomalies, records)
            if isinstance(anomaly_result, tuple):
                anomaly_text, anomaly_flags = anomaly_result
                anomaly_graph_buf = await asyncio.to_thread(graphs.generate_anomaly_scatter_plot, records, anomaly_flags)
            else:
                anomaly_text = anomaly_result

        pdf_bytes = await asyncio.to_thread(
            export.create_pdf, 
            adv_report, abc_report, opt_text, graph_buf, opt_graph_buf, anomaly_text, anomaly_graph_buf
        )
        
        pdf_file = BufferedInputFile(pdf_bytes, filename="Financial_Report.pdf")
        await msg.delete()
        await callback.message.answer_document(document=pdf_file, caption="📄 <b>Ваш комплексный финансовый отчет готов!</b>", parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка при создании PDF: {e}", exc_info=True)
        await msg.edit_text("❌ Произошла ошибка при создании PDF-документа. Пожалуйста, попробуйте позже.")
    finally:
        await callback.answer()

@router.callback_query(F.data == "find_anomalies")
async def process_find_anomalies(callback: types.CallbackQuery):
    records = await database.get_financial_records(callback.from_user.id)
    if not records:
        await callback.message.answer("❌ У вас пока нет данных. Пожалуйста, загрузите Excel-отчет.")
    else:
        result = await asyncio.to_thread(analytics.detect_anomalies, records)
        if isinstance(result, tuple):
            report, anomaly_flags = result
            graph_buf = await asyncio.to_thread(graphs.generate_anomaly_scatter_plot, records, anomaly_flags)
            
            if graph_buf:
                photo = BufferedInputFile(graph_buf.read(), filename="anomalies.png")
                await callback.message.answer_photo(photo=photo, caption=report, parse_mode="HTML")
            else:
                await callback.message.answer(report, parse_mode="HTML")
        else:
            await callback.message.answer(result, parse_mode="HTML")
    await callback.answer()

@router.message(F.document)
async def process_document(message: types.Message, bot: Bot):
    document = message.document
    if not document.file_name.endswith(('.xls', '.xlsx')):
        await message.answer("❌ Пожалуйста, отправьте файл в формате Excel (.xlsx).")
        return
        
    msg = await message.answer("📥 Файл получен! Читаю и анализирую данные...")
    
    os.makedirs("downloads", exist_ok=True)
    destination = f"downloads/{message.from_user.id}_{document.file_name}"
    await bot.download(document, destination=destination)
    
    try:
        xls = await asyncio.to_thread(pd.read_excel, destination, sheet_name=None, dtype={'Месяц': str})
        
        df_fin = None
        df_prod = None
        
        for name, df in xls.items():
            if 'Выручка' in df.columns or 'Постоянные_расходы' in df.columns:
                df_fin = df
            elif 'Наименование_товара' in df.columns:
                df_prod = df
                
        if df_fin is None or df_prod is None:
            await msg.edit_text("❌ Ошибка: Не удалось найти листы с финансами и товарами. Проверьте названия колонок.")
            return
        
        def parse_date(val):
            if isinstance(val, (datetime, pd.Timestamp)):
                return val.date()
                
            val_str = str(val).strip()
            if '.' in val_str:
                parts = val_str.split('.')
                if len(parts) == 2:
                    val_str = f"{parts[0].zfill(2)}.{parts[1]}"
                    return datetime.strptime(val_str, "%m.%Y").date()
                    
            return pd.to_datetime(val).date()

        fin_records = []
        for _, row in df_fin.iterrows():
            period = parse_date(row['Месяц'])
            fin_records.append((
                period, float(row['Выручка']), float(row['Постоянные_расходы']),
                float(row['Переменные_расходы']), float(row['Налоги_и_кредиты']),
                float(row['Бюджет_маркетинг']), int(row['Новые_клиенты']), float(row['Остатки_на_складе'])
            ))
            
        prod_records = []
        for _, row in df_prod.iterrows():
            period = parse_date(row['Месяц'])
            
            cost = float(row['Себестоимость_товара']) if 'Себестоимость_товара' in df_prod.columns else 0.0
            
            stock = int(row['Остаток_на_конец_месяца_шт']) if 'Остаток_на_конец_месяца_шт' in df_prod.columns else 0
            
            prod_records.append((
                period, 
                str(row['Наименование_товара']), 
                int(row['Количество_продаж']), 
                float(row['Выручка_с_товара']),
                cost,
                stock
            ))
            
        await database.clear_user_data(message.from_user.id)
        
        await database.insert_financial_records(message.from_user.id, fin_records)
        await database.insert_product_sales(message.from_user.id, prod_records)
        
        await msg.edit_text("✅ Данные из Excel успешно загружены и сохранены в базу данных!\n\nТеперь вы можете нажать кнопку «Аналитика и тренды» или «ABC-анализ товаров».", reply_markup=get_main_menu())
        
    except Exception as e:
        logging.error(f"Ошибка парсинга Excel: {e}")
        await msg.edit_text("❌ Произошла ошибка при чтении файла.\nУбедитесь, что названия колонок точно совпадают с шаблоном.")
    finally:
        if os.path.exists(destination):
            os.remove(destination)

@router.message(F.text)
async def process_nlp_transaction(message: types.Message, state: FSMContext):
    if message.text.startswith('/'):
        return
        
    amount, category = analytics.process_natural_language_transaction(message.text)
    
    if amount and category:
        if category == "unknown":
            await state.update_data(nlp_amount=amount, nlp_text=message.text)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💵 Выручка", callback_data="nlp_cat_revenue")],
                [InlineKeyboardButton(text="🏭 Постоянные расходы", callback_data="nlp_cat_fixed_costs")],
                [InlineKeyboardButton(text="📦 Переменные расходы", callback_data="nlp_cat_variable_costs")],
                [InlineKeyboardButton(text="📢 Маркетинг", callback_data="nlp_cat_marketing_budget")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="nlp_cat_cancel")]
            ])
            await message.reply(f"🤷‍♂️ Я понял, что сумма <b>{amount:,.0f} ₽</b>, но не знаю, куда отнести этот текст.\n\n<i>Подскажите категорию, и я запомню эту фразу навсегда!</i>", reply_markup=keyboard, parse_mode="HTML")
            await state.set_state(NLPTrainingState.waiting_for_category)
            return
            
        cat_names = {
            "revenue": "💵 Выручка",
            "fixed_costs": "🏭 Постоянные расходы",
            "variable_costs": "📦 Переменные расходы",
            "marketing_budget": "📢 Маркетинг"
        }
        try:
            await database.add_micro_transaction(message.from_user.id, amount, category)
            await message.reply(
                f"🤖 <b>NLP-Анализ:</b> Транзакция распознана!\n"
                f"Сумма: <b>{amount:,.0f} ₽</b>\n"
                f"Категория: <b>{cat_names[category]}</b>\n"
                f"<i>✅ Записана в текущий месяц.</i>",
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Ошибка БД при NLP транзакции: {e}")
            await message.reply("❌ Ошибка при сохранении в базу данных.")

@router.callback_query(NLPTrainingState.waiting_for_category, F.data.startswith("nlp_cat_"))
async def process_nlp_training(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.replace("nlp_cat_", "")
    
    if action == "cancel":
        await callback.message.edit_text("❌ Операция отменена.")
        await state.clear()
        return
        
    data = await state.get_data()
    amount = data.get('nlp_amount')
    
    if amount is None:
        await callback.message.edit_text("⏳ <i>Эта операция уже была обработана или устарела.</i>", parse_mode="HTML")
        await state.clear()
        return
        
    text = data.get('nlp_text')
    
    is_learned = analytics.add_new_phrase_and_retrain(text, action)
    
    await database.add_micro_transaction(callback.from_user.id, amount, action)
    
    cat_names = {
        "revenue": "💵 Выручка", "fixed_costs": "🏭 Постоянные расходы",
        "variable_costs": "📦 Переменные расходы", "marketing_budget": "📢 Маркетинг"
    }
    
    if is_learned:
        await callback.message.edit_text(f"✅ <b>Запомнил!</b> Теперь похожие фразы будут относиться к категории <b>{cat_names[action]}</b>.\n\nСумма <b>{amount:,.0f} ₽</b> записана в текущий месяц.", parse_mode="HTML")
    else:
        await callback.message.edit_text(f"✅ Сумма <b>{amount:,.0f} ₽</b> записана в категорию <b>{cat_names[action]}</b>.\n\n<i>ℹ️ Текст состоял только из цифр или общих слов (например, «заплатил»), поэтому для ИИ новых правил не создано. В следующий раз напишите чуть подробнее (например: «заплатил за интернет»).</i>", parse_mode="HTML")
    await state.clear()
