import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from finbot import config
from finbot.bot.handlers import router
from finbot.bot.scheduler import send_weekly_summary
from finbot.db import database


async def main() -> None:
    config.validate()
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    await database.init_db_pool(config.DATABASE_URL)

    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="help", description="Справка по боту"),
    ])

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_weekly_summary, "cron", day_of_week="fri", hour=18, minute=0, args=(bot,))
    scheduler.start()

    logging.info("Бот запущен и подключен к БД")
    await dp.start_polling(bot)


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
