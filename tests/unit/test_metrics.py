"""Unit tests for PPA metrics extraction and report parsers."""

from autosilix.metrics import MetricsExtractor


def test_parse_synthesis_report(tmp_path):
    rpt_path = tmp_path / "reports" / "synthesis.rpt"
    rpt_path.parent.mkdir(parents=True, exist_ok=True)
    rpt_path.write_text("""
=== sequence_detector ===
   Number of wires:                 12
   Number of cells:                 18
     $_DFF_P_                       3
     $_AND_                         6
   Chip area for module 'sequence_detector': 124.50 um^2
""", encoding="utf-8")

    metrics = MetricsExtractor.extract_all(tmp_path)
    assert "cell_area" in metrics
    assert metrics["cell_area"]["value"] == 124.50
    assert metrics["cell_area"]["unit"] == "um^2"
    assert metrics["cell_count"]["value"] == 18
    assert metrics["sequential_cell_count"]["value"] == 3


def test_parse_sta_report(tmp_path):
    rpt_path = tmp_path / "reports" / "sta.rpt"
    rpt_path.parent.mkdir(parents=True, exist_ok=True)
    rpt_path.write_text("""
AutoSilix Static Timing Analysis (STA) Report
Clock target: 10.000 ns
Worst Negative Slack (WNS): 0.000 ns
Total Negative Slack (TNS): 0.000 ns
Critical path delay: 4.180 ns
Slack: 5.570 ns
""", encoding="utf-8")

    metrics = MetricsExtractor.extract_all(tmp_path)
    assert metrics["clock_target"]["value"] == 10.0
    assert metrics["worst_negative_slack"]["value"] == 0.0
    assert metrics["critical_path_delay"]["value"] == 4.18
    assert metrics["setup_slack"]["value"] == 5.57


def test_empty_or_corrupt_report_handling(tmp_path):
    rpt_path = tmp_path / "reports" / "sta.rpt"
    rpt_path.parent.mkdir(parents=True, exist_ok=True)
    rpt_path.write_text("random broken content without matching fields", encoding="utf-8")

    # Should not raise exception
    metrics = MetricsExtractor.extract_all(tmp_path)
    assert metrics == {}
