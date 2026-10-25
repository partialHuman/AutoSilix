"""Failure-injection integration tests simulating errors, timeouts, and missing files."""


import pytest

from autosilix.artifacts import ArtifactManager
from autosilix.config import ConfigManager
from autosilix.exceptions import ArtifactError, ConfigurationError
from autosilix.stages import StageState
from autosilix.workflow import WorkflowEngine


def test_failure_on_missing_rtl_source(tmp_path):
    bad_cfg = tmp_path / "bad_rtl.yaml"
    bad_cfg.write_text("""
schema_version: "1.0.0"
design:
  name: "missing_rtl_design"
  top_module: "missing_top"
  rtl_files: ["nonexistent_path/fake_rtl.v"]
pdk:
  name: "sky130"
flow:
  stages: ["synthesis"]
""", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="RTL source file declared in configuration not found"):
        ConfigManager.load(bad_cfg)


def test_failure_on_tool_not_found(sample_config, tmp_path):
    # Running without mock when tools are not installed should fail honestly
    engine = WorkflowEngine(
        config=sample_config,
        run_id="fail_no_tool",
        base_runs_dir=tmp_path,
        mock=False,
    )
    manifest = engine.run()
    assert manifest.status == "FAIL"
    # Existing artifacts preserved
    assert (engine.artifacts.run_dir / "manifest.json").is_file()
    assert len(manifest.errors) >= 1


def test_failure_duplicate_run_id_collision(sample_config, tmp_path):
    # Initialize run directory and write file
    mgr1 = ArtifactManager("sequence_detector", "collision_run", base_runs_dir=tmp_path)
    r_dir = mgr1.initialize_run_dir()
    (r_dir / "data.txt").write_text("prior data", encoding="utf-8")

    # Second initialization without overwrite must raise ArtifactError
    mgr2 = ArtifactManager("sequence_detector", "collision_run", base_runs_dir=tmp_path)
    with pytest.raises(ArtifactError, match="already exists and is not empty"):
        mgr2.initialize_run_dir(overwrite=False)


def test_workflow_fail_fast_skips_downstream(sample_config, tmp_path):
    # Without tools, rtl_simulation will fail, so synthesis and routing must be SKIPPED
    sample_config.flow.fail_fast = True
    engine = WorkflowEngine(
        config=sample_config,
        run_id="test_fail_fast",
        base_runs_dir=tmp_path,
        mock=False,
    )
    manifest = engine.run()
    assert manifest.status == "FAIL"

    stages = manifest.stages
    # First stage failed
    assert stages["rtl_simulation"].state == StageState.FAIL
    # Downstream stages skipped
    assert stages["synthesis"].state == StageState.SKIPPED
    assert stages["floorplan"].state == StageState.SKIPPED
    assert stages["routing"].state == StageState.SKIPPED
