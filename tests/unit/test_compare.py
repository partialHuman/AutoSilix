"""Unit tests for PPA run comparison engine and safety checks."""

import json

import pytest

from autosilix.compare import RunComparator
from autosilix.exceptions import IncompatibleComparisonError


def create_mock_manifest(tmp_path, run_id, design, metrics):
    m_path = tmp_path / run_id / "manifest.json"
    m_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "design_name": design,
        "status": "PASS",
        "duration_seconds": 10.0,
        "metrics": metrics,
    }
    m_path.write_text(json.dumps(data), encoding="utf-8")
    return m_path


def test_compare_compatible_runs(tmp_path):
    m_a = create_mock_manifest(
        tmp_path, "run_A", "sequence_detector",
        {"cell_area": {"value": 100.0, "unit": "um^2"}, "setup_slack": {"value": 2.0, "unit": "ns"}}
    )
    m_b = create_mock_manifest(
        tmp_path, "run_B", "sequence_detector",
        {"cell_area": {"value": 120.0, "unit": "um^2"}, "setup_slack": {"value": 1.5, "unit": "ns"}}
    )

    res = RunComparator.compare_runs(m_a, m_b)
    assert res["run_a"]["run_id"] == "run_A"
    assert res["run_b"]["run_id"] == "run_B"

    area_comp = next(m for m in res["metrics"] if m["metric"] == "cell_area")
    assert area_comp["delta"] == 20.0
    assert area_comp["pct_change"] == 20.0

    slack_comp = next(m for m in res["metrics"] if m["metric"] == "setup_slack")
    assert slack_comp["delta"] == -0.5
    assert slack_comp["pct_change"] == -25.0


def test_compare_incompatible_designs_raises(tmp_path):
    m_a = create_mock_manifest(tmp_path, "run_A", "sequence_detector", {})
    m_b = create_mock_manifest(tmp_path, "run_B", "alu_accumulator", {})

    with pytest.raises(IncompatibleComparisonError, match="Incompatible run comparison"):
        RunComparator.compare_runs(m_a, m_b, strict_design_check=True)
