from _data import load_records
from finbot.analytics import detect_anomalies
from finbot.reporting import graphs

PNG = b"\x89PNG\r\n\x1a\n"


def test_dashboard_is_png():
    fin, _ = load_records()
    assert graphs.generate_dashboard_graphs(fin).read(8) == PNG


def test_anomaly_scatter_is_png():
    fin, _ = load_records()
    _, flags = detect_anomalies(fin)
    assert graphs.generate_anomaly_scatter_plot(fin, flags).read(8) == PNG
