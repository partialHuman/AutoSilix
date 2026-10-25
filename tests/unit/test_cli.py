"""Unit tests for AutoSilix CLI interface."""

import pytest

from autosilix.cli import main


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "AutoSilix" in captured.out


def test_cli_tools(capsys):
    ret = main(["tools"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "AutoSilix EDA Toolchain Audit" in captured.out


def test_cli_validate(sample_config_path, capsys):
    ret = main(["validate", "--config", str(sample_config_path)])
    assert ret == 0
    captured = capsys.readouterr()
    assert "[OK] Configuration" in captured.out


def test_cli_run_mock(sample_config_path, tmp_path, capsys):
    ret = main([
        "run",
        "--config", str(sample_config_path),
        "--mock",
        "--runs-dir", str(tmp_path),
        "--run-id", "test_cli_run",
    ])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Workflow Summary" in captured.out
    assert "Status: PASS" in captured.out


def test_cli_status_and_report(sample_config_path, tmp_path, capsys):
    # Run once
    main([
        "run",
        "--config", str(sample_config_path),
        "--mock",
        "--runs-dir", str(tmp_path),
        "--run-id", "test_status_run",
    ])

    # Check status
    ret_stat = main(["status", "--run-id", "test_status_run", "--runs-dir", str(tmp_path)])
    assert ret_stat == 0

    # Check report
    ret_rep = main(["report", "--run-id", "test_status_run", "--runs-dir", str(tmp_path), "--format", "json"])
    assert ret_rep == 0
