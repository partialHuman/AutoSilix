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
