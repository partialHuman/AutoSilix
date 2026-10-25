"""Test configuration and shared fixtures for AutoSilix."""

from pathlib import Path

import pytest

from autosilix.config import AutoSilixConfig, ConfigManager


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def sample_config_path(repo_root) -> Path:
    return repo_root / "configs" / "designs" / "sequence_detector.yaml"


@pytest.fixture
def sample_config(sample_config_path, repo_root) -> AutoSilixConfig:
    return ConfigManager.load(sample_config_path, workspace_root=repo_root)


@pytest.fixture
def temp_run_dir(tmp_path) -> Path:
    d = tmp_path / "runs"
    d.mkdir(parents=True, exist_ok=True)
    return d
