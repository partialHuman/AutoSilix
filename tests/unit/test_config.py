"""Unit tests for configuration manager and schema validation."""

from pathlib import Path

import pytest
import yaml

from autosilix.config import ConfigManager
from autosilix.exceptions import ConfigurationError, ValidationError


def test_valid_config_loading(sample_config_path, repo_root):
    cfg = ConfigManager.load(sample_config_path, workspace_root=repo_root)
    assert cfg.design.name == "sequence_detector"
    assert cfg.design.top_module == "sequence_detector"
    assert len(cfg.design.rtl_files) >= 1
    assert Path(cfg.design.rtl_files[0]).is_file()
    assert cfg.constraints.clock_period == 10.0
    assert cfg.config_hash != ""


def test_missing_config_file(tmp_path):
    with pytest.raises(ConfigurationError, match="Configuration file not found"):
        ConfigManager.load(tmp_path / "nonexistent.yaml")


def test_malformed_yaml(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("design: [unclosed list", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="Malformed YAML"):
        ConfigManager.load(bad_yaml)


def test_schema_missing_required_property(tmp_path):
    invalid = tmp_path / "invalid.yaml"
    # Missing 'pdk' and 'flow'
    data = {
        "schema_version": "1.0.0",
        "design": {
            "name": "foo",
            "top_module": "foo",
            "rtl_files": ["foo.v"],
        },
    }
    invalid.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValidationError):
        ConfigManager.load(invalid)


def test_schema_invalid_stage_name(tmp_path):
    invalid = tmp_path / "invalid_stage.yaml"
    data = {
        "schema_version": "1.0.0",
        "design": {
            "name": "foo",
            "top_module": "foo",
            "rtl_files": ["foo.v"],
        },
        "pdk": {"name": "sky130"},
        "flow": {
            "stages": ["invalid_stage_xyz"],
        },
    }
    invalid.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValidationError):
        ConfigManager.load(invalid)


def test_missing_rtl_file_raises_error(tmp_path):
    cfg_file = tmp_path / "missing_rtl.yaml"
    data = {
        "schema_version": "1.0.0",
        "design": {
            "name": "foo",
            "top_module": "foo",
            "rtl_files": ["does_not_exist_xyz.v"],
        },
        "pdk": {"name": "sky130"},
        "flow": {"stages": ["synthesis"]},
    }
    cfg_file.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="RTL source file declared in configuration not found"):
        ConfigManager.load(cfg_file)
