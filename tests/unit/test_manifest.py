"""Unit tests for manifest generation, updates, and schema compliance."""

import json

from autosilix.manifest import Manifest
from autosilix.stages import StageResult, StageState


def test_manifest_lifecycle(tmp_path):
    run_dir = tmp_path / "test_run"
    m = Manifest(
        run_id="run_test_123",
        design_name="sequence_detector",
        config_hash="abc12345",
        run_dir=run_dir,
    )
    assert m.status == "PENDING"
    assert m.manifest_path.is_file()

    # Update stage
    s1 = StageResult(name="rtl_simulation", state=StageState.PASS, duration_seconds=0.5, exit_code=0)
    m.update_stage(s1)

    loaded = json.loads(m.manifest_path.read_text(encoding="utf-8"))
    assert loaded["stages"]["rtl_simulation"]["state"] == "PASS"

    # Finalize
    m.finalize()
    assert m.status == "PASS"
    assert m.duration_seconds is not None

    final_loaded = Manifest.load(m.manifest_path)
    assert final_loaded["status"] == "PASS"
    assert final_loaded["schema_version"] == "1.0.0"
