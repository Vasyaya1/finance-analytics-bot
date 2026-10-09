from _data import load_records
from finbot.analytics import detect_anomalies


def test_requires_at_least_six_months():
    fin, _ = load_records()
    assert isinstance(detect_anomalies(fin[:5]), str)


def test_flags_match_number_of_records():
    fin, _ = load_records()
    result = detect_anomalies(fin)
    assert isinstance(result, tuple)
    report, flags = result
    assert len(flags) == len(fin)
    assert set(flags) <= {1, -1}


def test_injected_collapse_is_detected():
    # синтетический «слив бюджета»: выручка падает втрое, маркетинг растёт втрое
    fin, _ = load_records()
    fin = [dict(r) for r in fin[:12]]
    fin[6]["revenue"] *= 0.3
    fin[6]["marketing_budget"] *= 3
    _, flags = detect_anomalies(fin)
    assert flags[6] == -1
