"""Unit tests for subprocess runner, logging, and timeouts."""

import sys

import pytest

from autosilix.exceptions import ToolNotFoundError
from autosilix.runner import SubprocessRunner


def test_runner_successful_command(tmp_path):
    log_file = tmp_path / "test.log"
    cmd = [sys.executable, "-c", "print('hello from runner')"]
    res = SubprocessRunner.run_command(cmd, log_file=log_file, capture_memory=True)

    assert res.returncode == 0
    assert not res.timed_out
    assert "hello from runner" in res.stdout
    assert log_file.is_file()
    assert "hello from runner" in log_file.read_text(encoding="utf-8")


def test_runner_nonzero_exit_code(tmp_path):
    log_file = tmp_path / "error.log"
    cmd = [sys.executable, "-c", "import sys; sys.exit(42)"]
    res = SubprocessRunner.run_command(cmd, log_file=log_file)

    assert res.returncode == 42
    assert not res.timed_out


def test_runner_missing_executable(tmp_path):
    cmd = ["nonexistent_exec_xyz_123", "--version"]
    with pytest.raises(ToolNotFoundError):
        SubprocessRunner.run_command(cmd)


def test_runner_timeout(tmp_path):
    log_file = tmp_path / "timeout.log"
    # Python script that sleeps for 2 seconds with timeout of 0.3s
    cmd = [sys.executable, "-c", "import time; time.sleep(2)"]
    res = SubprocessRunner.run_command(cmd, log_file=log_file, timeout=0.3)

    assert res.timed_out is True
    assert log_file.is_file()
    assert "timed out" in log_file.read_text(encoding="utf-8")
