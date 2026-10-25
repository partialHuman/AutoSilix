"""Unit tests for stage states, dependencies, and contracts."""

from autosilix.stages import (
    STAGE_CONTRACTS,
    STAGE_DEPENDENCIES,
    STAGE_ORDER,
    StageResult,
    StageState,
)


def test_stage_states_values():
    assert StageState.PENDING.value == "PENDING"
    assert StageState.PASS.value == "PASS"
    assert StageState.FAIL.value == "FAIL"
    assert StageState.SKIPPED.value == "SKIPPED"
    assert StageState.UNSUPPORTED.value == "UNSUPPORTED"


def test_stage_order_completeness():
    assert "rtl_simulation" in STAGE_ORDER
    assert "synthesis" in STAGE_ORDER
    assert "floorplan" in STAGE_ORDER
    assert "routing" in STAGE_ORDER
    assert "gds_export" in STAGE_ORDER


def test_stage_dependencies():
    assert STAGE_DEPENDENCIES["synthesis"] == ["rtl_simulation"]
    assert STAGE_DEPENDENCIES["floorplan"] == ["synthesis"]
    assert STAGE_DEPENDENCIES["routing"] == ["cts"]


def test_stage_contracts():
    for name in ["synthesis", "routing", "sta", "gds_export"]:
        contract = STAGE_CONTRACTS[name]
        assert contract.name == name
        assert len(contract.expected_outputs) >= 1


def test_stage_result_to_dict():
    res = StageResult(
        name="synthesis",
        state=StageState.PASS,
        duration_seconds=1.2345,
        exit_code=0,
        artifacts=["netlists/synthesized.v"],
    )
    d = res.to_dict()
    assert d["name"] == "synthesis"
    assert d["state"] == "PASS"
    assert d["duration_seconds"] == round(1.2345, 3)
    assert d["artifacts"] == ["netlists/synthesized.v"]
