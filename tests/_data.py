"""Хелперы тестов: превращают демо-Excel в записи того же вида, что отдаёт asyncpg (dict-подобные)."""
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent / "data"
DEMO = ROOT / "demo"
SCENARIOS = Path(os.getenv("SCENARIO_DIR", ROOT / "scenarios"))


def _period(value: str):
    month, year = value.split(".")
    return pd.Timestamp(year=int(year), month=int(month), day=1).date()


def load_records(name: str = "demo_normal.xlsx", folder: Path = DEMO):
    sheets = pd.read_excel(folder / name, sheet_name=None, dtype={"Месяц": str})
    fin, prod = sheets["Финансы"], sheets["Товары"]
    fin_records = [
        {
            "period": _period(r["Месяц"]),
            "revenue": float(r["Выручка"]),
            "fixed_costs": float(r["Постоянные_расходы"]),
            "variable_costs": float(r["Переменные_расходы"]),
            "taxes": float(r["Налоги_и_кредиты"]),
            "marketing_budget": float(r["Бюджет_маркетинг"]),
            "new_customers": int(r["Новые_клиенты"]),
            "inventory_value": float(r["Остатки_на_складе"]),
        }
        for _, r in fin.iterrows()
    ]
    prod_records = [
        {
            "period": _period(r["Месяц"]),
            "product_name": str(r["Наименование_товара"]),
            "quantity_sold": int(r["Количество_продаж"]),
            "product_revenue": float(r["Выручка_с_товара"]),
            "product_cost": float(r["Себестоимость_товара"]),
            "stock_qty": int(r["Остаток_на_конец_месяца_шт"]) if "Остаток_на_конец_месяца_шт" in prod.columns else 0,
        }
        for _, r in prod.iterrows()
    ]
    return fin_records, prod_records
