"""Integration tests for RTL designs, testbenches, and functional verification."""

import shutil

import pytest

from autosilix.runner import SubprocessRunner


def test_sequence_detector_rtl_files_exist(repo_root):
    rtl = repo_root / "designs" / "sequence_detector" / "rtl" / "sequence_detector.v"
    tb = repo_root / "designs" / "sequence_detector" / "tb" / "tb_sequence_detector.v"
    sdc = repo_root / "designs" / "sequence_detector" / "constraints" / "sky130_constraints.sdc"

    assert rtl.is_file() and rtl.stat().st_size > 0
    assert tb.is_file() and tb.stat().st_size > 0
    assert sdc.is_file() and sdc.stat().st_size > 0


def test_alu_accumulator_rtl_files_exist(repo_root):
    rtl = repo_root / "designs" / "alu_accumulator" / "rtl" / "alu_accumulator.v"
    tb = repo_root / "designs" / "alu_accumulator" / "tb" / "tb_alu_accumulator.v"
    sdc = repo_root / "designs" / "alu_accumulator" / "constraints" / "sky130_constraints.sdc"

    assert rtl.is_file() and rtl.stat().st_size > 0
    assert tb.is_file() and tb.stat().st_size > 0
    assert sdc.is_file() and sdc.stat().st_size > 0


def test_sequence_detector_behavioral_logic():
    """Verify exact state transitions of sequence detector logic."""
    states = {"IDLE": 0, "S1": 1, "S10": 2, "S101": 3}
    curr_state = states["IDLE"]

    def step(curr, bit):
        if curr == states["IDLE"]:
            nxt = states["S1"] if bit else states["IDLE"]
        elif curr == states["S1"]:
            nxt = states["S1"] if bit else states["S10"]
        elif curr == states["S10"]:
            nxt = states["S101"] if bit else states["IDLE"]
        elif curr == states["S101"]:
            nxt = states["S1"] if bit else states["S10"]
        else:
            nxt = states["IDLE"]

        detect = (curr == states["S101"] and bit == 1)
        return nxt, detect

    # Test sequence: 1, 0, 1, 1 (detect), 0, 1, 1 (detect via overlap!)
    curr_state, d = step(curr_state, 1)
    assert d is False
    curr_state, d = step(curr_state, 0)
    assert d is False
    curr_state, d = step(curr_state, 1)
    assert d is False
    curr_state, d = step(curr_state, 1)
    assert d is True  # 1011 detected!

    # Overlapping continuation: next bit 0 -> state S10
    curr_state, d = step(curr_state, 0)
    assert d is False
    curr_state, d = step(curr_state, 1)
    assert d is False
    curr_state, d = step(curr_state, 1)
    assert d is True  # Second 1011 detected via overlap!


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog not installed on system PATH")
def test_real_iverilog_simulation(repo_root, tmp_path):
    rtl = repo_root / "designs" / "sequence_detector" / "rtl" / "sequence_detector.v"
    tb = repo_root / "designs" / "sequence_detector" / "tb" / "tb_sequence_detector.v"

    vvp_out = tmp_path / "sim.vvp"
    log_out = tmp_path / "sim.log"

    c_res = SubprocessRunner.run_command(["iverilog", "-o", str(vvp_out), "-g2012", str(rtl), str(tb)], log_file=log_out)
    assert c_res.returncode == 0

    r_res = SubprocessRunner.run_command(["vvp", str(vvp_out)], log_file=log_out)
    assert r_res.returncode == 0
    assert "TEST PASSED" in log_out.read_text(encoding="utf-8")
