"""Конфигурация из переменных окружения (.env)."""
import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")


def validate() -> None:
    missing = [k for k, v in {"BOT_TOKEN": BOT_TOKEN, "DATABASE_URL": DATABASE_URL}.items() if not v]
    if missing:
        raise RuntimeError(
            f"Не заданы переменные окружения: {', '.join(missing)}. "
            "Скопируйте .env.example в .env и заполните значения."
        )
