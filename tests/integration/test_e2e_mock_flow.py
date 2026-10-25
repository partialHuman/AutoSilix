"""End-to-end integration tests for complete implementation workflows."""

from autosilix.config import ConfigManager
from autosilix.manifest import Manifest
from autosilix.workflow import WorkflowEngine


def test_e2e_sequence_detector_mock_flow(sample_config, tmp_path):
    engine = WorkflowEngine(
        config=sample_config,
        run_id="e2e_test_seq",
        base_runs_dir=tmp_path,
        mock=True,
    )
    manifest = engine.run()
    assert manifest.status == "PASS"

    # Verify manifest on disk
    m_disk = Manifest.load(engine.artifacts.run_dir / "manifest.json")
    assert m_disk["status"] == "PASS"
    assert m_disk["design_name"] == "sequence_detector"

    # Verify all expected artifacts exist
    assert (engine.artifacts.run_dir / "netlists" / "synthesized.v").is_file()
    assert (engine.artifacts.run_dir / "reports" / "synthesis.rpt").is_file()
    assert (engine.artifacts.run_dir / "databases" / "routed.def").is_file()
    assert (engine.artifacts.run_dir / "layout" / "final.gds").is_file()

    # Verify metrics extracted
    metrics = m_disk["metrics"]
    assert "cell_area" in metrics
    assert "setup_slack" in metrics
    assert "wire_length" in metrics


def test_e2e_alu_accumulator_mock_flow(repo_root, tmp_path):
    alu_cfg_path = repo_root / "configs" / "designs" / "alu_accumulator.yaml"
    alu_cfg = ConfigManager.load(alu_cfg_path, workspace_root=repo_root)

    engine = WorkflowEngine(
        config=alu_cfg,
        run_id="e2e_test_alu",
        base_runs_dir=tmp_path,
        mock=True,
    )
    manifest = engine.run()
    assert manifest.status == "PASS"

    m_disk = Manifest.load(engine.artifacts.run_dir / "manifest.json")
    assert m_disk["design_name"] == "alu_accumulator"
    assert "cell_area" in m_disk["metrics"]
