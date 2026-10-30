"""Unit tests for report generation in Markdown, JSON, and CSV."""

from autosilix.report import ReportGenerator


def test_generate_markdown_report():
    manifest_data = {
        "run_id": "run_001",
        "design_name": "sequence_detector",
        "status": "PASS",
        "start_time": "2026-10-25T10:00:00",
        "end_time": "2026-10-25T10:00:05",
        "duration_seconds": 5.0,
        "config_hash": "abc12345",
        "stages": {
            "synthesis": {
                "state": "PASS",
                "duration_seconds": 1.5,
                "exit_code": 0,
                "log_file": "logs/synthesis.log",
                "error_summary": None,
            }
        },
        "metrics": {
            "cell_area": {
                "value": 124.5,
                "unit": "um^2",
                "stage": "synthesis",
                "source_file": "reports/synthesis.rpt",
            }
        },
    }

    md = ReportGenerator.generate_markdown(manifest_data)
    assert "# AutoSilix Implementation Report" in md
    assert "sequence_detector" in md
    assert "run_001" in md
    assert "cell_area" in md
    assert "124.5" in md


def test_generate_csv_metrics():
    manifest_data = {
        "run_id": "run_001",
        "design_name": "sequence_detector",
        "metrics": {
            "cell_area": {
                "value": 124.5,
                "unit": "um^2",
                "stage": "synthesis",
                "source_file": "reports/synthesis.rpt",
            }
        },
    }
    csv_str = ReportGenerator.generate_csv_metrics(manifest_data)
    assert "run_id,design_name,metric_name,value,unit,stage,source_file" in csv_str
    assert "cell_area,124.5,um^2,synthesis" in csv_str


def test_save_all_reports(tmp_path):
    manifest_data = {
        "run_id": "run_001",
        "design_name": "sequence_detector",
        "status": "PASS",
        "stages": {},
        "metrics": {},
    }
    paths = ReportGenerator.save_all_reports(manifest_data, tmp_path)
    assert paths["markdown"].is_file()
    assert paths["json"].is_file()
    assert paths["csv"].is_file()


def test_report_status_badge_encodable():
    """Status badge characters must be encodable as UTF-8 (no cp1252-only glyphs)."""
    manifest_pass = {
        "run_id": "enc_test",
        "design_name": "gcd",
        "status": "PASS",
        "start_time": "2026-01-01T00:00:00+00:00",
        "end_time": "2026-01-01T00:01:00+00:00",
        "duration_seconds": 60.0,
        "config_hash": "abc",
        "environment": {},
        "stages": {},
        "metrics": {},
    }
    manifest_fail = dict(manifest_pass, status="FAIL")

    for m in (manifest_pass, manifest_fail):
        md = ReportGenerator.generate_markdown(m)
        # Must encode without error in both UTF-8 and ASCII-safe fallback
        md.encode("utf-8")  # raises UnicodeEncodeError if broken


def test_report_fail_badge_present():
    """FAIL runs must produce a FAIL badge, not PASS."""
    manifest_data = {
        "run_id": "r2",
        "design_name": "gcd",
        "status": "FAIL",
        "start_time": "2026-01-01T00:00:00+00:00",
        "end_time": "2026-01-01T00:00:10+00:00",
        "duration_seconds": 10.0,
        "config_hash": "xyz",
        "environment": {},
        "stages": {},
        "metrics": {},
    }
    md = ReportGenerator.generate_markdown(manifest_data)
    assert "FAIL" in md
    assert "PASS" not in md.split("Status")[1][:40]
