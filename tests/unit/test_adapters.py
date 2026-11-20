"""Unit tests for tool adapters and script generators."""


from autosilix.adapters import get_adapter_for_stage
from autosilix.adapters.openroad import OpenRoadAdapter
from autosilix.adapters.simulator import SimulatorAdapter
from autosilix.adapters.yosys import YosysAdapter
from autosilix.artifacts import ArtifactManager
from autosilix.stages import StageState


def test_get_adapter_registry():
    assert isinstance(get_adapter_for_stage("rtl_simulation"), SimulatorAdapter)
    assert isinstance(get_adapter_for_stage("synthesis"), YosysAdapter)
    assert isinstance(get_adapter_for_stage("floorplan"), OpenRoadAdapter)
    assert isinstance(get_adapter_for_stage("routing"), OpenRoadAdapter)


def test_simulator_adapter_mock(sample_config, tmp_path):
    mgr = ArtifactManager("sequence_detector", "run_sim_test", base_runs_dir=tmp_path)
    mgr.initialize_run_dir()
    adapter = SimulatorAdapter()
    res = adapter.execute(sample_config, mgr, mock=True)

    assert res.state == StageState.PASS
    assert res.exit_code == 0
    assert (mgr.run_dir / "logs" / "rtl_simulation.log").is_file()


def test_yosys_adapter_mock(sample_config, tmp_path):
    mgr = ArtifactManager("sequence_detector", "run_synth_test", base_runs_dir=tmp_path)
    mgr.initialize_run_dir()
    adapter = YosysAdapter()
    res = adapter.execute(sample_config, mgr, mock=True)

    assert res.state == StageState.PASS
    assert (mgr.run_dir / "netlists" / "synthesized.v").is_file()
    assert (mgr.run_dir / "reports" / "synthesis.rpt").is_file()
    assert (mgr.run_dir / "config" / "synthesis.tcl").is_file()


def test_openroad_adapter_mock(sample_config, tmp_path):
    mgr = ArtifactManager("sequence_detector", "run_or_test", base_runs_dir=tmp_path)
    mgr.initialize_run_dir()
    adapter = OpenRoadAdapter("routing")
    res = adapter.execute(sample_config, mgr, mock=True)

    assert res.state == StageState.PASS
    assert (mgr.run_dir / "databases" / "routed.def").is_file()
    assert (mgr.run_dir / "reports" / "routing.rpt").is_file()


def test_simulator_adapter_mock_gcd(tmp_path):
    """GCD design mock simulation should invoke math.gcd reference model and PASS."""
    from pathlib import Path

    import yaml

    from autosilix.config import ConfigManager

    # Build a minimal config pointing at a real RTL file
    rtl_path = Path(__file__).resolve().parents[2] / "experiments" / "gcd" / "exp05" / "gcd.v"
    if not rtl_path.is_file():
        import pytest
        pytest.skip("GCD exp05 RTL not present")

    cfg_data = {
        "schema_version": "1.0.0",
        "design": {
            "name": "gcd",
            "top_module": "gcd",
            "rtl_files": [str(rtl_path)],
            "tb_files": [str(rtl_path)],  # dummy tb path - mock won't use it
        },
        "pdk": {"name": "sky130"},
        "flow": {"stages": ["rtl_simulation"]},
    }
    cfg_file = tmp_path / "gcd_test.yaml"
    cfg_file.write_text(yaml.safe_dump(cfg_data), encoding="utf-8")
    cfg = ConfigManager.load(cfg_file)

    mgr = ArtifactManager("gcd", "run_gcd_mock", base_runs_dir=tmp_path)
    mgr.initialize_run_dir()
    adapter = SimulatorAdapter()
    res = adapter.execute(cfg, mgr, mock=True)

    assert res.state == StageState.PASS
    log_text = (mgr.run_dir / "logs" / "rtl_simulation.log").read_text(encoding="utf-8")
    assert "TEST PASSED" in log_text
    assert "math.gcd" in log_text or "GCD verified" in log_text


def test_unknown_stage_raises():
    """Requesting an adapter for an unknown stage must raise ValueError."""
    import pytest

    from autosilix.adapters import get_adapter_for_stage
    with pytest.raises(ValueError, match="Unknown workflow stage"):
        get_adapter_for_stage("nonexistent_stage_xyz")
