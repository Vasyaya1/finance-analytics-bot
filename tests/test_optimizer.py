from _data import load_records
from finbot.analytics import generate_optimization_report

BUDGET = 500_000


def test_allocation_uses_whole_budget_and_is_non_negative():
    fin, prod = load_records()
    report, allocation = generate_optimization_report(prod, fin, budget=BUDGET)
    total = sum(allocation.values())
    assert 0.95 * BUDGET <= total <= 1.001 * BUDGET
    assert all(v >= 0 for v in allocation.values())
    assert "Маркетинг" in allocation


def test_overstocked_sku_gets_no_budget():
    fin, prod = load_records()
    prod = [dict(r) for r in prod]
    last = max(r["period"] for r in prod)
    for r in prod:
        if r["product_name"] == "Чехол силиконовый" and r["period"] == last:
            r["stock_qty"] = 100_000  # запасов на годы вперёд
    _, allocation = generate_optimization_report(prod, fin, budget=BUDGET)
    assert "Чехол силиконовый" not in allocation


def test_missing_cost_data_returns_error_message():
    fin, prod = load_records()
    prod = [{**r, "product_cost": 0.0} for r in prod]
    assert isinstance(generate_optimization_report(prod, fin, budget=BUDGET), str)
