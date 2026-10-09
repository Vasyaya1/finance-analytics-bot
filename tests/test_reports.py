from _data import load_records
from finbot import analytics


def test_basic_report_contains_core_metrics():
    fin, _ = load_records()
    report = analytics.generate_basic_analytics_report(fin)
    assert "EBITDA" in report and "ROS" in report


def test_abc_report_has_classes():
    fin, prod = load_records()
    report = analytics.generate_abc_report(prod, fin)
    assert "Класс" in report


def test_what_if_report_builds_for_last_month():
    fin, _ = load_records()
    assert isinstance(analytics.generate_what_if_report(fin[-1]), str)
