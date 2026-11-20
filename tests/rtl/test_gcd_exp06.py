"""Tests for Experiment 06 (experiments/gcd/exp06).

* Python-model verification of the cycle-level behaviour.
* Consistency of the directed-test count, RTL hash and reported status across the
  testbench, the Python script, the README and ppa_results.json.
* Optional Icarus Verilog simulation of tb_gcd_exp06.v (skipped when iverilog is absent).
"""

import hashlib
import importlib.util
import json
import re
import shutil

import pytest

from autosilix.runner import SubprocessRunner

EXP06_DIR = "experiments/gcd/exp06"


@pytest.fixture
def exp06(repo_root):
    return repo_root / EXP06_DIR


@pytest.fixture
def verify_module(exp06):
    spec = importlib.util.spec_from_file_location("verify_exp06", exp06 / "verify_exp06.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def results(exp06):
    return json.loads((exp06 / "ppa_results.json").read_text(encoding="utf-8"))


def test_python_model_verification(verify_module):
    summary = verify_module.run_all(seed=7, random_vectors=2000, exhaustive8=False)
    assert summary["status"] == "PASS"
    assert summary["directed_cases"] == len(verify_module.DIRECTED_CASES)
    monitor = summary["monitor"]
    assert monitor["responses"] == monitor["latency_checks"] > 0
    assert monitor["stability_checks"] > 0


def test_directed_case_literals_are_independent(verify_module):
    for a, b, expected in verify_module.DIRECTED_CASES:
        assert expected == verify_module.euclid_gcd(a, b)


def test_directed_count_consistent(exp06, verify_module, results):
    testbench = (exp06 / "tb_gcd_exp06.v").read_text(encoding="utf-8")
    calls = re.findall(r"^\s*run_case\(\s*(\d+),\s*(\d+),\s*(\d+),", testbench, re.MULTILINE)
    from_tb = [(int(a), int(b), int(e)) for a, b, e in calls]
    assert from_tb == verify_module.DIRECTED_CASES
    count = len(from_tb)
    assert results["functional_verification"]["directed_cases"] == count
    assert results["functional_verification"]["python_model"]["directed_cases"] == count
    assert f"{count} directed" in (exp06 / "README.md").read_text(encoding="utf-8")


def test_rtl_hash_matches_results(exp06, results):
    data = (exp06 / "gcd.v").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(data).hexdigest() == results["rtl_sha256"]


def test_results_do_not_claim_timing_closure(results):
    assert results["timing_closed"] is False
    assert results["placement_measured"]["setup_wns_ns"] < 0
    assert results["placement_measured"]["min_clock_period_ns"] > results["clock_period_target_ns"]
    assert results["routed_measured"] is None


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog not installed on system PATH")
def test_rtl_simulation_passes(exp06, tmp_path):
    simulation = tmp_path / "sim_exp06.vvp"
    log = tmp_path / "sim.log"
    compile_cmd = [
        "iverilog",
        "-g2012",
        "-s",
        "tb_gcd_exp06",
        "-o",
        str(simulation),
        str(exp06 / "gcd.v"),
        str(exp06 / "tb_gcd_exp06.v"),
    ]
    compiled = SubprocessRunner.run_command(compile_cmd, log_file=log, timeout=120)
    assert compiled.returncode == 0
    ran = SubprocessRunner.run_command(["vvp", str(simulation)], log_file=log, timeout=900)
    assert ran.returncode == 0
    assert "ALL TESTS PASSED: 26 directed" in log.read_text(encoding="utf-8")
