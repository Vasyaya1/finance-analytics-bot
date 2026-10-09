import re

from _data import SCENARIOS, load_records
from finbot import analytics

BUDGET = 500_000
TAG = re.compile(r"<[^>]+>")


def _load(name):
    return load_records(name, SCENARIOS)


def _optimize(name):
    fin, prod = _load(name)
    report, allocation = analytics.generate_optimization_report(prod, fin, budget=BUDGET)
    return TAG.sub("", report), allocation


def _anomalies(name):
    fin, _ = _load(name)
    report, flags = analytics.detect_anomalies(fin)
    return TAG.sub("", report), flags


def test_total_oos_all_skus_critical_and_marketing_is_zero():
    report, allocation = _optimize("test_4_total_oos.xlsx")
    assert report.count("КРИТИЧЕСКИЙ ДЕФИЦИТ") == 7
    assert allocation.get("Маркетинг", 0) < 0.01 * BUDGET  # весь бюджет уходит на срочную закупку


def test_margin_trap_funds_high_margin_sku_in_deficit():
    report, allocation = _optimize("test_5_margin_trap.xlsx")
    assert allocation.get("Чехол силиконовый", 0) > 0
    assert "КРИТИЧЕСКИЙ ДЕФИЦИТ" in report


def test_toxic_marketing_detected_and_marketing_cut_to_zero():
    report, flags = _anomalies("test_6_toxic_marketing.xlsx")
    assert flags[-1] == -1
    assert "Токсичный маркетинг" in report
    _, allocation = _optimize("test_6_toxic_marketing.xlsx")
    assert allocation.get("Маркетинг", 0) < 0.01 * BUDGET  # отрицательная эластичность маркетинга


def test_toxic_marketing_flags_limited_by_contamination():
    # Задокументированное ограничение: contamination=0.1 => флаги на ~10 % месяцев,
    # поэтому из 6 «токсичных» месяцев помечается не больше половины.
    _, flags = _anomalies("test_6_toxic_marketing.xlsx")
    assert 1 <= flags.count(-1) <= 4


def test_hype_train_last_months_flagged_and_socks_in_deficit():
    _, flags = _anomalies("test_7_hype_train.xlsx")
    assert flags[-1] == -1 and flags[-2] == -1
    report, allocation = _optimize("test_7_hype_train.xlsx")
    assert "КРИТИЧЕСКИЙ ДЕФИЦИТ" in report
    assert allocation.get("Носки Хлопковые (набор)", 0) > 0


def test_organic_hype_without_ad_spend_gets_viral_hypothesis():
    # В test_7 реклама растёт вместе с выручкой (10 % выручки), поэтому гипотеза «вирусный эффект»
    # там недостижима. В test_7b рекламный бюджет не меняется — правило должно сработать.
    report, flags = _anomalies("test_7b_hype_organic.xlsx")
    assert flags[-1] == -1
    assert "Взрывной органический рост" in report


def test_loss_leader_gets_no_investment():
    _, allocation = _optimize("test_8_loss_leader.xlsx")
    assert allocation.get("Куртка Зимняя Premium", 0) < 0.01 * BUDGET  # продаётся ниже себестоимости


def test_seasonal_crash_blocks_overstocked_anchor():
    report, allocation = _optimize("test_9_seasonal_crash.xlsx")
    assert allocation.get("Куртка Зимняя Premium", 0) < 0.01 * BUDGET
    assert "Затоваривание" in report


def test_missing_stock_column_returns_data_error():
    # Так выглядел исходный test_9: колонки «Остаток_на_конец_месяца_шт» нет -> остатки = 0.
    fin, prod = _load("test_9_seasonal_crash.xlsx")
    prod = [{**r, "stock_qty": 0} for r in prod]
    result = analytics.generate_optimization_report(prod, fin, budget=BUDGET)
    assert isinstance(result, str) and "Ошибка данных" in result
