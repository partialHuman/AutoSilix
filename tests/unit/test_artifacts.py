"""Unit tests for artifact manager, directory isolation, and hashing."""


import pytest

from autosilix.artifacts import ArtifactManager
from autosilix.exceptions import ArtifactError


def test_artifact_manager_creation(tmp_path):
    mgr = ArtifactManager(design_name="test_design", run_id="run_001", base_runs_dir=tmp_path)
    run_dir = mgr.initialize_run_dir()

    assert run_dir.exists()
    for sub in mgr.SUBDIRECTORIES:
        assert (run_dir / sub).is_dir()


def test_artifact_collision_protection(tmp_path):
    mgr1 = ArtifactManager(design_name="test_design", run_id="run_001", base_runs_dir=tmp_path)
    run_dir1 = mgr1.initialize_run_dir()
    # Add a dummy file inside run directory
    (run_dir1 / "logs" / "test.log").write_text("data", encoding="utf-8")

    # Attempting to re-initialize same run without overwrite should raise ArtifactError
    mgr2 = ArtifactManager(design_name="test_design", run_id="run_001", base_runs_dir=tmp_path)
    with pytest.raises(ArtifactError, match="already exists and is not empty"):
        mgr2.initialize_run_dir(overwrite=False)


def test_config_snapshot(tmp_path):
    mgr = ArtifactManager(design_name="test_design", run_id="run_002", base_runs_dir=tmp_path)
    mgr.initialize_run_dir()
    cfg_data = {"design": {"name": "test_design"}, "schema_version": "1.0.0"}
    snap_path = mgr.snapshot_config(cfg_data)

    assert snap_path.is_file()
    assert "test_design" in snap_path.read_text(encoding="utf-8")


def test_compute_sha256(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("AutoSilix reproducible verification", encoding="utf-8")
    h = ArtifactManager.compute_sha256(f)
    assert len(h) == 64
    assert h == ArtifactManager.compute_sha256(f)
